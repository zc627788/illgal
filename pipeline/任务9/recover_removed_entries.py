"""
任务9-5：从 removed_entries.csv 恢复符合条件的法条

根据 Correction on Mapping from violated law to violation_categories.md 的 (1-5) 部分:
扫描 removed_entries.csv，筛选法条中含有指定关键词的记录，按规则赋予分类后恢复到词典中。

新增处理：
1. 对恢复的法条进行清洗（去掉左右多余内容）
2. 过滤不含书名号的法条
3. 过滤结尾无效的法条
4. 去重（恢复条目自身去重 + 与词典合并后去重）
"""

import pandas as pd
import re
from pathlib import Path
import logging
from datetime import datetime

# ============ 关键词-分类映射 ============

KEYWORD_CATEGORY_MAP = {
    "公共场所卫生管理条例": "卫生健康",
    "作业规程": "安全生产",
    "商品质量": "产品质量",
    "成品油质量监督抽查": "产品质量",
    "清理长期停业": "未开业/自行停业",
    "GB/T": "产品质量",
    "GB19147": "计量/器具",
    "GB5296": "产品质量",
    "GB7718": "食品药品",
    "JJG": "计量/器具",
    "QB/T": "产品质量",
    "食用油销售与召回": "食品药品",
    "上市公司信息披露": "金融/账户",
    "公共汽车和电车乘坐规则": "交通运输违规",
    "出租汽车管理": "交通运输违规",
    "航道法": "交通运输违规",
    "邮政法": "交通运输违规",
    "河道管理": "海事安全",
    "航标条例": "海事安全",
    "专利": "侵犯商标/知识产权",
    "著作权法": "侵犯商标/知识产权",
    "传染病防治法": "卫生健康",
    "卫生管理": "卫生健康",
    "国境卫生检疫法": "海关/进出口/卫生健康",
    "劳动合同法": "劳动保障/用工",
    "尘肺病防治": "劳动保障/用工",
    "职业防治法": "劳动保障/用工",
    "合同法": "消费者权益/市场秩序",
    "电子商务法": "网络市场交易/市场秩序",
    "中华人民共和国水法": "环境保护",
    "草原法": "环境保护",
    "防洪法": "环境保护",
    "黄河保护法": "环境保护",
    "长江保护法": "环境保护",
    "海关行政处罚实施条例": "海关/进出口",
    "进出境": "海关/进出口",
    "电信条例": "网络/数据安全",
    "网络完全法": "网络/数据安全",
    "中华人民共和国药典": "食品药品",
    "计量检定": "计量/器具",
    "计量法": "计量/器具",
    "伪劣商品": "产品质量",
    "互联网": "公共文化与传媒",
    "保安服务": "治安管理",
    "兽药": "农业",
    "农田保护": "农业",
    "建筑法": "建设工程",
}

# ============ 清洗函数 ============

def clean_legal_article(article):
    """清洗法条，去除前后无意义内容"""
    if pd.isna(article):
        return article, False, None
    
    text = str(article).strip()
    original = text
    changes = []
    
    # 前缀清理
    prefixes = [
        (r'^依据\d*[\.、]?\s*', '去除前缀"依据"'),
        (r'^根据\s*', '去除前缀"根据"'),
        (r'^参照\s*', '去除前缀"参照"'),
        (r'^按照\s*', '去除前缀"按照"'),
        (r'^依照\s*', '去除前缀"依照"'),
    ]
    for pattern, desc in prefixes:
        if re.search(pattern, text):
            text = re.sub(pattern, '', text)
            changes.append(desc)
            break
    
    # 截断无效结尾
    valid_ending_patterns = [
        r'(的规定|之规定)',
        r'(\)项|\）项|\(项|\（项)',
        r'(\)款|\）款|\(款|\（款)',
        r'(第[一二三四五六七八九十百千零\d]+[条款项章节号])',
        r'(\([一二三四五六七八九十\d]+\))',
        r'(\（[一二三四五六七八九十\d]+\）)',
        r'(》|>|＞)',
    ]
    
    combined_pattern = '|'.join(valid_ending_patterns)
    if not re.search(f'({combined_pattern})$', text):
        last_valid_pos = -1
        for pattern in valid_ending_patterns:
            for match in re.finditer(pattern, text):
                if match.end() > last_valid_pos:
                    last_valid_pos = match.end()
        
        if last_valid_pos > 0 and last_valid_pos < len(text):
            truncated = text[last_valid_pos:]
            text = text[:last_valid_pos]
            changes.append(f'截断后缀"{truncated[:20]}..."' if len(truncated) > 20 else f'截断后缀"{truncated}"')
    
    is_changed = text != original
    return text, is_changed, '; '.join(changes) if changes else None


def check_no_book_quote(article):
    """检查是否不含书名号"""
    if pd.isna(article):
        return True, "空值"
    text = str(article)
    if '《' not in text and '》' not in text:
        return True, f"(6-8) 不含书名号 | {text[:50]}"
    return False, None


def check_invalid_ending(article):
    """检查结尾是否无效"""
    if pd.isna(article):
        return True, "空值"
    text = str(article).strip()
    
    valid_endings = [
        r'》$',
        r'第[一二三四五六七八九十百千零\d]+[条款项章节号]$',
        r'\([一二三四五六七八九十\d]+\)$',
        r'（[一二三四五六七八九十\d]+）$',
        r'[)）]项$',
        r'[)）]款$',
        r'的规定$',
        r'之规定$',
    ]
    
    for pattern in valid_endings:
        if re.search(pattern, text):
            return False, None
    
    return True, f"(6-9) 无效结尾 | {text[:50]}"


def setup_logging(log_dir: Path):
    log_file = log_dir / f"recover_entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def match_keyword(legal_article: str) -> tuple[str, str]:
    if pd.isna(legal_article):
        return None, None
    for keyword, category in KEYWORD_CATEGORY_MAP.items():
        if keyword in legal_article:
            return category, keyword
    return None, None


def main(dry_run: bool = False):
    script_dir = Path(__file__).parent
    task8_dir = script_dir.parent / "任务8- 去掉法条左右多余"
    
    removed_file = task8_dir / "removed_entries.csv"
    corrected_file = script_dir / "去掉法条左右多余信息_corrected.csv"
    recovered_file = script_dir / "recovered_entries.csv"
    final_file = script_dir / "去掉法条左右多余信息_final.csv"
    filtered_file = script_dir / "recovered_filtered_out.csv"
    
    logger = setup_logging(script_dir)
    logger.info(f"开始处理: {removed_file}")
    
    df_removed = pd.read_csv(removed_file, encoding='utf-8')
    logger.info(f"读取 {len(df_removed)} 行被删除条目")
    
    keyword_stats = {}
    matched_count = 0
    cleaned_count = 0
    no_book_quote_count = 0
    invalid_ending_count = 0
    
    recovered = []
    filtered_out = []
    
    for idx, row in df_removed.iterrows():
        legal_article = row['legal_articles']
        
        category, matched_keyword = match_keyword(legal_article)
        if category is None:
            continue
        
        matched_count += 1
        keyword_stats[matched_keyword] = keyword_stats.get(matched_keyword, 0) + 1
        
        cleaned_article, is_changed, change_desc = clean_legal_article(legal_article)
        if is_changed:
            cleaned_count += 1
        
        should_remove, reason = check_no_book_quote(cleaned_article)
        if should_remove:
            filtered_out.append({
                'legal_articles': legal_article,
                'cleaned_article': cleaned_article,
                'filter_reason': reason,
                'matched_keyword': matched_keyword
            })
            no_book_quote_count += 1
            continue
        
        should_remove, reason = check_invalid_ending(cleaned_article)
        if should_remove:
            filtered_out.append({
                'legal_articles': legal_article,
                'cleaned_article': cleaned_article,
                'filter_reason': reason,
                'matched_keyword': matched_keyword
            })
            invalid_ending_count += 1
            continue
        
        recovered.append({
            'legal_articles': cleaned_article,
            'legal_violation_categories': category,
            'violation_keywords': matched_keyword,
            'is_generic': False,
            'before_legal_categories': '',
            'reason_ai': f'从removed恢复: 匹配关键词 {matched_keyword}' + (f', 清洗: {change_desc}' if change_desc else ''),
            'original_big_category': category,
        })
    
    logger.info(f"关键词匹配: {matched_count} 条")
    logger.info(f"清洗修改: {cleaned_count} 条")
    logger.info(f"过滤-无书名号: {no_book_quote_count} 条")
    logger.info(f"过滤-无效结尾: {invalid_ending_count} 条")
    logger.info(f"恢复候选: {len(recovered)} 条")
    
    # ===== 恢复条目自身去重 =====
    df_recovered = pd.DataFrame(recovered)
    before_self_dedup = len(df_recovered)
    df_recovered = df_recovered.drop_duplicates(subset=['legal_articles'], keep='first')
    after_self_dedup = len(df_recovered)
    if before_self_dedup > after_self_dedup:
        logger.info(f"恢复条目自身去重: {before_self_dedup} -> {after_self_dedup}")
    
    logger.info(f"最终恢复: {len(df_recovered)} 条")
    
    logger.info("\n关键词匹配统计:")
    for keyword, count in sorted(keyword_stats.items(), key=lambda x: -x[1]):
        logger.info(f"  {keyword}: {count}")
    
    if dry_run:
        logger.info("\n[DRY RUN] 未保存任何文件")
        logger.info("恢复示例 (前10条):")
        for _, row in df_recovered.head(10).iterrows():
            logger.info(f"  {row['legal_articles'][:50]}... -> {row['legal_violation_categories']}")
    else:
        if len(df_recovered) > 0:
            df_recovered.to_csv(recovered_file, index=False, encoding='utf-8')
            logger.info(f"已保存恢复条目: {recovered_file}")
            
            if filtered_out:
                df_filtered = pd.DataFrame(filtered_out)
                df_filtered.to_csv(filtered_file, index=False, encoding='utf-8')
                logger.info(f"已保存过滤条目: {filtered_file}")
            
            if corrected_file.exists():
                df_corrected = pd.read_csv(corrected_file, encoding='utf-8')
                logger.info(f"读取已修正词典: {len(df_corrected)} 行")
                
                cols = ['legal_articles', 'legal_violation_categories', 'violation_keywords', 
                        'is_generic', 'before_legal_categories', 'reason_ai', 'original_big_category']
                df_recovered_clean = df_recovered[cols]
                
                df_final = pd.concat([df_corrected, df_recovered_clean], ignore_index=True)
                
                before_len = len(df_final)
                df_final = df_final.drop_duplicates(subset=['legal_articles'], keep='first')
                logger.info(f"合并后去重: {before_len} -> {len(df_final)}")
                
                df_final.to_csv(final_file, index=False, encoding='utf-8')
                logger.info(f"已保存最终词典: {final_file}")
            else:
                logger.warning(f"未找到已修正词典: {corrected_file}")
    
    return len(df_recovered)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='从 removed_entries.csv 恢复符合条件的法条')
    parser.add_argument('--dry-run', action='store_true', help='仅统计, 不保存文件')
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)
