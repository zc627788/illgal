# -*- coding: utf-8 -*-
"""
任务8：去掉法条左右多余内容 + 去重
功能：
1. 清洗法条前缀（依据、根据等）
2. 找到最后一个有效法条编号位置，截断后面多余内容
3. 去重（基于legal_articles列）
4. 输出清洗后的CSV、修改记录、重复记录
"""

import pandas as pd
import re
import os


def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def clean_legal_article(article):
    """
    清洗法条，去除前后无意义内容
    核心规则：找到最后一个有效法条编号位置，截断后面多余内容
    返回: (清洗后的法条, 是否修改, 修改说明)
    """
    if pd.isna(article):
        return article, False, None
    
    text = str(article).strip()
    original = text
    changes = []
    
    # ===== 1. 前缀清理 =====
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
    
    # ===== 2. 找到最后一个有效结尾位置，截断后面内容 =====
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
    if re.search(f'({combined_pattern})$', text):
        pass
    else:
        last_valid_pos = -1
        for pattern in valid_ending_patterns:
            for match in re.finditer(pattern, text):
                end_pos = match.end()
                if end_pos > last_valid_pos:
                    last_valid_pos = end_pos
        
        if last_valid_pos > 0 and last_valid_pos < len(text):
            truncated = text[last_valid_pos:]
            text = text[:last_valid_pos]
            changes.append(f'截断后缀"{truncated[:20]}..."' if len(truncated) > 20 else f'截断后缀"{truncated}"')
    
    is_changed = text != original
    change_desc = '; '.join(changes) if changes else None
    
    return text, is_changed, change_desc


def main():
    script_dir = get_script_dir()
    
    input_file = os.path.join(script_dir, "任务7_清洗后词典.csv")
    output_cleaned = os.path.join(script_dir, "任务8_清洗去重后词典.csv")
    output_changes = os.path.join(script_dir, "任务8_修改记录.csv")
    output_duplicates = os.path.join(script_dir, "任务8_重复记录.csv")
    
    print("=" * 60)
    print("任务8：去掉法条左右多余内容 + 去重")
    print("=" * 60)
    
    print(f"\n读取文件: {input_file}")
    df = pd.read_csv(input_file)
    print(f"原始数据行数: {len(df)}")
    
    # ===== Step 1: 清洗法条 =====
    print("\n[Step 1] 清洗法条...")
    changes_log = []
    cleaned_count = 0
    
    for idx, row in df.iterrows():
        original = row['legal_articles']
        cleaned, is_changed, change_desc = clean_legal_article(original)
        
        if is_changed:
            changes_log.append({
                'original_article': original,
                'cleaned_article': cleaned,
                'change_description': change_desc,
                'legal_violation_categories': row['legal_violation_categories']
            })
            df.at[idx, 'legal_articles'] = cleaned
            cleaned_count += 1
    
    print(f"清洗完成，共修改 {cleaned_count} 条法条")
    
    # ===== Step 2: 去重 =====
    print("\n[Step 2] 去重...")
    before_dedup = len(df)
    
    # 记录重复的条目
    duplicates = df[df.duplicated(subset=['legal_articles'], keep='first')].copy()
    
    # 去重（保留第一个）
    df = df.drop_duplicates(subset=['legal_articles'], keep='first')
    
    after_dedup = len(df)
    removed_count = before_dedup - after_dedup
    print(f"去重完成，删除 {removed_count} 条重复记录")
    print(f"去重后行数: {after_dedup}")
    
    # ===== 保存结果 =====
    df.to_csv(output_cleaned, index=False, encoding='utf-8')
    print(f"\n清洗+去重后数据已保存: {output_cleaned}")
    
    if changes_log:
        df_changes = pd.DataFrame(changes_log)
        df_changes.to_csv(output_changes, index=False, encoding='utf-8')
        print(f"修改记录已保存: {output_changes} ({len(df_changes)}条)")
    
    if len(duplicates) > 0:
        duplicates.to_csv(output_duplicates, index=False, encoding='utf-8')
        print(f"重复记录已保存: {output_duplicates} ({len(duplicates)}条)")
    
    print("\n" + "=" * 60)
    print("处理完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()
