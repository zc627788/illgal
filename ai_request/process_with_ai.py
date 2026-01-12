"""
AI并发处理脚本
功能：
1. 读取预测结果CSV，过滤需要AI处理的数据(need_ai=1)
3. 每次响应立即写入，避免数据丢失
4. 支持断点续传（跳过已处理的行）
"""

import pandas as pd
import asyncio
import aiohttp
import re
import os
import time
import threading
import json
from datetime import datetime
import sys

# Windows 环境下的 asyncio 兼容性修复
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from config import (
    API_URL, API_KEY, MODEL_NAME, MAX_CONCURRENT, 
    INPUT_FILE, OUTPUT_FILE, REQUEST_TIMEOUT, 
    MAX_RETRIES, PROMPT_TEMPLATE,
    PROMPT_TEMPLATE_RULE_HINT, APPEND_NEW_AI_COLUMNS,
    AI_ENABLE_LOG, AI_LOG_FILE, RETRY_FAILED_ONLY
)

# 线程锁，确保写入安全
write_lock = threading.Lock()
log_lock = threading.Lock()

# 全局变量
processed_ids = set()
df_output = pd.DataFrame()  # 全局输出 DataFrame，用于支持原位更新


def write_ai_log(event: dict):
    if not AI_ENABLE_LOG:
        return

    try:
        with log_lock:
            with open(AI_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _clean_text(val) -> str:
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.lower() == "nan":
        return ""
    return s


def _clean_rule_categories(val) -> str:
    s = _clean_text(val)
    if not s:
        return ""
    parts = [p.strip() for p in re.split(r"\s*\|\|\s*", s) if p.strip()]
    parts = [p for p in parts if p != "其他违法行为"]
    return "||".join(parts)


def _get_output_columns():
    if APPEND_NEW_AI_COLUMNS:
        return "ai_violation_categories_v2", "ai_reason_v2", "ai_raw_response_v2", "process_status_v2"
    return "ai_violation_categories", "ai_reason", "ai_raw_response", "process_status"


def _build_prompt(text: str, row_data: dict) -> str:
    """根据是否存在 violation_categories 决定使用哪套 prompt。"""
    rule_categories = _clean_rule_categories(row_data.get("violation_categories", ""))
    if rule_categories:
        return PROMPT_TEMPLATE_RULE_HINT.format(text=text, rule_categories=rule_categories)
    return PROMPT_TEMPLATE.format(text=text)


def load_processed_ids():
    """加载已处理的ID，支持断点续传"""
    global processed_ids, df_output
    if os.path.exists(OUTPUT_FILE):
        try:
            out_cat_col, out_reason_col, out_raw_col, out_status_col = _get_output_columns()
            
            # 加载整个文件到内存以便后续原位更新
            df_output = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')

            if APPEND_NEW_AI_COLUMNS and out_status_col in df_output.columns:
                status = df_output[out_status_col].fillna('').astype(str).str.strip()
                processed_ids = set(df_output.loc[status != '', 'vc_id'].astype(str).tolist())
            else:
                processed_ids = set(df_output['vc_id'].astype(str).tolist())
            print(f"已加载 {len(processed_ids)} 条已处理记录")
        except Exception as e:
            print(f"加载已处理记录失败: {e}")
            processed_ids = set()
            df_output = pd.DataFrame()
    else:
        df_output = pd.DataFrame()




def init_output_file(columns):
    """初始化输出文件（如果不存在则创建表头）"""
    global df_output
    if not os.path.exists(OUTPUT_FILE):
        # 创建空的CSV文件，只有表头
        df_output = pd.DataFrame(columns=columns)
        df_output.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')
        print(f"创建输出文件: {OUTPUT_FILE}")
    elif df_output.empty:
        # 如果文件存在但 df_output 为空（可能加载失败），则重新加载
        df_output = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')


def parse_ai_response(response_text):
    """
    解析AI返回的内容，提取违规类别和判断理由
    """
    ai_category = ""
    ai_reason = ""

    generic_sections = re.findall(r"【[^】]+】[：:]\s*(.+?)(?=【[^】]+】|$)", response_text, flags=re.DOTALL)
    if len(generic_sections) >= 2:
        ai_category = generic_sections[0].strip()
        ai_reason = generic_sections[1].strip()
        ai_category = re.sub(r"[\n\r]", "", ai_category).split("\n")[0].strip()
        ai_reason = re.sub(r"[\n\r]+", " ", ai_reason).strip()
    
    # 尝试匹配【违规类别】
    category_patterns = [
        r'【违规类别】[：:]\s*(.+?)(?=【|$)',
        r'违规类别[：:]\s*(.+?)(?=【|判断|$)',
        r'类别[：:]\s*(.+?)(?=【|$)',
    ]

    if not ai_category:
        for pattern in category_patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                ai_category = match.group(1).strip()
                # 清理多余字符
                ai_category = re.sub(r'[\n\r]', '', ai_category)
                ai_category = ai_category.split('\n')[0].strip()
                break
    
    # 尝试匹配【判断理由】
    reason_patterns = [
        r'【判断理由】[：:]\s*(.+?)(?=【|$)',
        r'判断理由[：:]\s*(.+?)(?=【|$)',
        r'理由[：:]\s*(.+?)(?=【|$)',
    ]

    if not ai_reason:
        for pattern in reason_patterns:
            match = re.search(pattern, response_text, re.DOTALL)
            if match:
                ai_reason = match.group(1).strip()
                # 清理换行符
                ai_reason = re.sub(r'[\n\r]+', ' ', ai_reason)
                break
    
    # 如果没匹配到，返回原始内容
    if not ai_category:
        ai_category = "解析失败"
    if not ai_reason:
        ai_reason = "解析失败"
    
    # 判断是否解析成功
    if ai_category == "解析失败" or ai_reason == "解析失败":
        return ai_category, ai_reason, "解析失败"
    else:
        return ai_category, ai_reason, "成功"


def write_result(row_dict):
    """线程安全地更新或写入单行结果到CSV"""
    global df_output
    with write_lock:
        # 清理文本中的换行符
        for key in row_dict:
            if isinstance(row_dict[key], str):
                row_dict[key] = row_dict[key].replace('\n', ' ').replace('\r', ' ').replace('\t', ' ')
        
        vc_id = str(row_dict['vc_id'])
        
        # 如果 vc_id 已存在且 df_output 不为空，执行原位更新
        if not df_output.empty and vc_id in df_output['vc_id'].astype(str).values:
            mask = df_output['vc_id'].astype(str) == vc_id
            for col, val in row_dict.items():
                if col in df_output.columns:
                    df_output.loc[mask, col] = val
        else:
            # 否则追加新行
            df_new_row = pd.DataFrame([row_dict])
            df_output = pd.concat([df_output, df_new_row], ignore_index=True)
        
        # 保存整个 DataFrame 到 CSV
        df_output.to_csv(OUTPUT_FILE, index=False, encoding='utf-8-sig')


async def call_ai_api(session, text, semaphore, row_data):
    """
    调用AI API
    """
    async with semaphore:
        vc_id = row_data['vc_id']

        out_cat_col, out_reason_col, out_raw_col, out_status_col = _get_output_columns()

        # 构建prompt
        prompt = _build_prompt(text, row_data)

        write_ai_log({
            "event": "request",
            "vc_id": str(vc_id),
            "rule_categories": _clean_rule_categories(row_data.get("violation_categories", "")),
            "text_len": len(text or ""),
            "prompt": prompt,
            "mode": "api",
        })
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}"
        }
        
        # 根据API格式调整请求体 (OpenAI兼容格式)
        payload = {
            "model": MODEL_NAME,
            "messages": [
                {"role": "system", "content": "你是一个专业的行政处罚案件分类专家，请根据处罚文本准确判断违规类别。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 500,
            "stream": False
        }
        
        # 直接处理，不重试 - 为每个请求创建独立的session
        try:
            async with aiohttp.ClientSession() as fresh_session:
                async with fresh_session.post(
                    API_URL, 
                    json=payload, 
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # 解析响应（根据API格式调整）
                        response_text = ""
                        if "choices" in result and len(result["choices"]) > 0:
                            response_text = result["choices"][0].get("message", {}).get("content", "")
                        elif "response" in result:
                            response_text = result["response"]
                        elif "content" in result:
                            response_text = result["content"]
                        else:
                            response_text = str(result)
                        
                        # 解析AI返回内容
                        ai_category, ai_reason, process_status = parse_ai_response(response_text)

                        write_ai_log({
                            "event": "response",
                            "vc_id": str(vc_id),
                            "status": process_status,
                            "ai_category": ai_category,
                            "ai_reason": ai_reason,
                            "raw_response": response_text,
                            "mode": "api",
                        })
                        
                        # 构建结果行
                        result_row = row_data.copy()
                        result_row[out_cat_col] = ai_category
                        result_row[out_reason_col] = ai_reason
                        result_row[out_raw_col] = response_text[:500]  # 保存原始响应（截断）
                        result_row[out_status_col] = process_status
                        
                        # 立即写入
                        write_result(result_row)
                        processed_ids.add(str(vc_id))
                        
                        return True, vc_id, ai_category
                    else:
                        error_msg = await response.text()
                        print(f"[{vc_id}] API错误 (状态码:{response.status}): {error_msg[:100]}")

                        write_ai_log({
                            "event": "error",
                            "vc_id": str(vc_id),
                            "status_code": response.status,
                            "error": error_msg,
                            "mode": "api",
                        })
                        
        except asyncio.TimeoutError:
            print(f"[{vc_id}] 请求超时")

            write_ai_log({
                "event": "error",
                "vc_id": str(vc_id),
                "error": "timeout",
                "mode": "api",
            })
        except Exception as e:
            print(f"[{vc_id}] 请求异常: {str(e)[:100]}")

            write_ai_log({
                "event": "error",
                "vc_id": str(vc_id),
                "error": str(e),
                "mode": "api",
            })
        
        # 处理失败
        result_row = row_data.copy()
        result_row[out_cat_col] = '请求失败'
        result_row[out_reason_col] = '请求失败'
        result_row[out_raw_col] = ''
        result_row[out_status_col] = '请求失败'
        
        write_result(result_row)
        processed_ids.add(str(vc_id))
        
        return False, vc_id, "请求失败"


async def process_batch(df_to_process):
    """批量处理数据"""
    # API模式 - 不使用共享session，每个请求创建独立session
    semaphore = asyncio.Semaphore(MAX_CONCURRENT)
    tasks = []
    
    for idx, row in df_to_process.iterrows():
        vc_id = str(row['vc_id'])
        
        # 跳过已处理的
        if vc_id in processed_ids:
            continue
        
        # 统一使用原文 text_combined
        text = str(row['text_combined']) if pd.notna(row['text_combined']) else ""
        row_data = row.to_dict()
        
        task = call_ai_api(None, text, semaphore, row_data)
        tasks.append(task)
    
    if not tasks:
        print("没有需要处理的新数据")
        return
    
    print(f"开始处理 {len(tasks)} 条数据，并发数: {MAX_CONCURRENT}")
    
    # 使用 tqdm 显示进度（如果可用）
    try:
        from tqdm.asyncio import tqdm_asyncio
        results = await tqdm_asyncio.gather(*tasks)
    except ImportError:
        print("tqdm 未安装，使用普通进度显示")
        results = await asyncio.gather(*tasks)
    
    # 统计结果
    success_count = sum(1 for r in results if r[0])
    fail_count = len(results) - success_count
    
    print(f"\n处理完成！成功: {success_count}, 失败: {fail_count}")


def main():
    global processed_ids    
    print("=" * 60)
    print("AI并发处理脚本 - API模式")
    print("=" * 60)
    
    print(f"使用API模型: {MODEL_NAME}")
    
    # 检查输入文件
    if not os.path.exists(INPUT_FILE):
        print(f"错误: 输入文件不存在 {INPUT_FILE}")
        print("请先运行 predict_with_trained_model.py 生成预测结果")
        return
    
    # 读取数据
    print(f"\n读取输入文件: {INPUT_FILE}")
    df = pd.read_csv(INPUT_FILE, encoding='utf-8-sig')
    print(f"总数据量: {len(df)} 条")
    
    # 过滤需要AI处理的数据 (need_ai=1)
    df_need_ai = df[df['need_ai'] == 1].copy()
    print(f"需要AI处理的数据: {len(df_need_ai)} 条 (need_ai=1)")
    
    # 按 vc_id 排序以保持顺序
    def extract_numeric_part(vc_id):
        """提取 vc_id 中的数字部分"""
        import re
        match = re.search(r'(\d+)', str(vc_id))
        return int(match.group(1)) if match else 0
    
    df_need_ai['vc_id_numeric'] = df_need_ai['vc_id'].apply(extract_numeric_part)
    df_need_ai = df_need_ai.sort_values(['vc_id_numeric', 'vc_id'], ascending=[True, True])
    df_need_ai = df_need_ai.drop('vc_id_numeric', axis=1)
    
    print(f"已按 vc_id 排序")
    
    if len(df_need_ai) == 0:
        print("没有需要AI处理的数据！")
        return
    
    # 添加新列（移除 process_time）
    out_cat_col, out_reason_col, out_raw_col, out_status_col = _get_output_columns()
    new_columns = list(df.columns)
    for c in [out_cat_col, out_reason_col, out_raw_col, out_status_col]:
        if c not in new_columns:
            new_columns.append(c)
    
    # 加载已处理的ID
    load_processed_ids()
    
    # 初始化输出文件
    init_output_file(new_columns)
    
    # 计算还需处理的数量
    if RETRY_FAILED_ONLY:
        out_cat_col, out_reason_col, out_raw_col, out_status_col = _get_output_columns()
        try:
            df_out = pd.read_csv(OUTPUT_FILE, encoding='utf-8-sig')
            failed_ids = set(df_out[df_out[out_status_col].isin(['解析失败', '请求失败'])]['vc_id'].astype(str).tolist())
            df_need_ai = df_need_ai[df_need_ai['vc_id'].astype(str).isin(failed_ids)].copy()
            # 从 processed_ids 中移除由 these 失败的 ID，确保它们被处理
            processed_ids -= failed_ids
            print(f"【重试模式】发现 {len(failed_ids)} 条记录状态为失败，将重新处理")
        except Exception as e:
            print(f"读取输出文件以进行重试失败: {e}")
            return

    remaining = len(df_need_ai[~df_need_ai['vc_id'].astype(str).isin(processed_ids)])
    print(f"还需处理: {remaining} 条")
    
    if remaining == 0:
        print("所有数据已完成或没有符合重试条件的记录！")
        return
    
    # 确认开始
    print(f"\n配置信息:")
    print(f"- 输入文件: {INPUT_FILE}")
    print(f"- 输出文件: {OUTPUT_FILE}")
    print(f"- 模型类型: API模型")
    
    print(f"- 并发数: {MAX_CONCURRENT}")
    
    # 开始处理
    asyncio.run(process_batch(df_need_ai))


if __name__ == "__main__":
    main()
