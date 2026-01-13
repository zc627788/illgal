"""
任务10：最终法条分类词典修正 (1-6)

功能：对 去掉法条左右多余信息_final.csv 进行少量修正
1. 应用 (1-3-2) 新增关键词覆盖
2. 食品药品关键词回补
3. 分类重命名
4. 双分类合并
"""

import pandas as pd
import re
from pathlib import Path
import logging
from datetime import datetime

# =====================================================================
# ====== 配置区域 - 从文档提取的映射数据 ======
# =====================================================================

# Step 2: (1-3-2) 新增关键词覆盖
KEYWORD_OVERRIDE_1_3_2 = {
"食品": "食品药品",
"保健食品": "食品药品",
"保健品": "食品药品",
"反不当竞争": "不正当竞争/商业贿赂",
"反不正竞争":"不正当竞争/商业贿赂",
"海关行政处罚": "海关/进出口"
}

# Step 1: 食品药品关键词列表
# 来自 (1-1), (1-2), (1-3-1), (1-3-2)
FOOD_DRUG_KEYWORDS = [
    # (1-1)
    "农产品质量安全法",
    "无公害农产品证书",
    "化妆品卫生标准",
    "饼干卫生标准",
    "供水卫生许可证",
    "食品安全",
    
    # (1-3-1)
    "中国药典",
    "医药有限公司",
    "农药",
    "动物检疫",
    "化妆品",
    "中药",
    "医药",
    "饲料质量",
    "饼干卫生",
    "藥商許可執照",
    "肥料",
    "饮用水",
    "城市供水",
    "饲料",
    "餐饮",
    "药品",
    "农产品",
    
    # (1-3-2)
    "食品",
    "保健食品",
    "保健品",
]

# Step 3: 分类重命名
CATEGORY_RENAME = {
    "网络安全": "网络/数据安全",
}

# Step 4: 双分类合并
DUAL_CATEGORY_MERGE = {
    "虚假广告/虚假宣传||侵犯商标/知识产权": "侵犯商标/知识产权",
    "金融/信贷违规||安全生产": "安全生产",
    "金融/信贷违规||交通运输违规": "交通运输违规",
    "金融/信贷违规||劳动保障/用工": "金融/信贷违规",
    "金融/信贷违规||房地产/土地": "金融/信贷违规",
    "金融/信贷违规||无照经营/登记问题": "金融/信贷违规",
    "安全生产/危化品||金融/信贷违规": "会计/账务",
}


# =====================================================================
# ====== 处理逻辑 - 不需要修改 ======
# =====================================================================

def setup_logging(log_dir: Path):
    """配置日志"""
    log_file = log_dir / f"task10_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def apply_keyword_override(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 2: 应用 (1-3-2) 关键词覆盖"""
    count = 0
    changes = []
    
    for idx, row in df.iterrows():
        legal_article = str(row['legal_articles'])
        old_category = row['legal_violation_categories']
        
        for keyword, target_category in KEYWORD_OVERRIDE_1_3_2.items():
            if keyword in legal_article:
                if row['legal_violation_categories'] != target_category:
                    changes.append({
                        'legal_articles': legal_article,
                        'old_category': old_category,
                        'new_category': target_category,
                        'rule': f'关键词覆盖 (1-3-2): {keyword}'
                    })
                    df.at[idx, 'legal_violation_categories'] = target_category
                    count += 1
                break  # 只应用第一个匹配的关键词
    
    return df, count, changes


def add_food_drug_category(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 1: 食品药品关键词回补"""
    count = 0
    changes = []
    
    # 检测"广告"或"登记"关键词的模式
    ad_keywords = ['广告']
    register_keywords = ['登记']
    
    for idx, row in df.iterrows():
        legal_article = str(row['legal_articles'])
        current_category = row['legal_violation_categories']
        
        # 检查是否包含"广告"或"登记"关键词
        has_ad_keyword = any(kw in legal_article for kw in ad_keywords)
        has_register_keyword = any(kw in legal_article for kw in register_keywords)
        
        if not (has_ad_keyword or has_register_keyword):
            continue
        
        # 检查是否包含食品药品关键词
        has_food_drug_keyword = any(kw in legal_article for kw in FOOD_DRUG_KEYWORDS)
        
        if has_food_drug_keyword:
            # 检查当前分类是否已包含"食品药品"
            if '食品药品' not in current_category:
                new_category = f"{current_category}||食品药品"
                changes.append({
                    'legal_articles': legal_article,
                    'old_category': current_category,
                    'new_category': new_category,
                    'rule': '食品药品关键词回补'
                })
                df.at[idx, 'legal_violation_categories'] = new_category
                count += 1
    
    return df, count, changes


def apply_category_rename(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 3: 分类重命名"""
    count = 0
    changes = []
    
    for idx, row in df.iterrows():
        category = row['legal_violation_categories']
        
        # 处理双分类（包含||）
        if '||' in str(category):
            parts = category.split('||')
            renamed_parts = [CATEGORY_RENAME.get(part, part) for part in parts]
            new_category = '||'.join(renamed_parts)
        else:
            new_category = CATEGORY_RENAME.get(category, category)
        
        if new_category != category:
            changes.append({
                'legal_articles': row['legal_articles'],
                'old_category': category,
                'new_category': new_category,
                'rule': '分类重命名'
            })
            df.at[idx, 'legal_violation_categories'] = new_category
            count += 1
    
    return df, count, changes


def apply_dual_category_merge(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Step 4: 双分类合并"""
    count = 0
    changes = []
    
    for idx, row in df.iterrows():
        category = str(row['legal_violation_categories'])
        
        if category in DUAL_CATEGORY_MERGE:
            new_category = DUAL_CATEGORY_MERGE[category]
            changes.append({
                'legal_articles': row['legal_articles'],
                'old_category': category,
                'new_category': new_category,
                'rule': '双分类合并'
            })
            df.at[idx, 'legal_violation_categories'] = new_category
            count += 1
    
    return df, count, changes


def main(dry_run: bool = False):
    """主处理函数"""
    # 路径配置
    script_dir = Path(__file__).parent
    input_file = script_dir.parent / "任务9" / "去掉法条左右多余信息_final.csv"
    output_file = script_dir / "去掉法条左右多余信息_最终版.csv"
    log_file = script_dir / "correction_log_task10.csv"
    
    logger = setup_logging(script_dir)
    logger.info(f"开始处理: {input_file}")
    
    # 读取数据
    df = pd.read_csv(input_file, encoding='gbk')
    logger.info(f"读取 {len(df)} 行")
    
    all_changes = []
    
    # Step 2: 应用 (1-3-2) 关键词覆盖
    logger.info("\n[Step 2] 应用 (1-3-2) 关键词覆盖...")
    df, count2, changes2 = apply_keyword_override(df)
    logger.info(f"修改 {count2} 条")
    all_changes.extend(changes2)
    
    # Step 1: 食品药品关键词回补
    logger.info("\n[Step 1] 食品药品关键词回补...")
    df, count1, changes1 = add_food_drug_category(df)
    logger.info(f"修改 {count1} 条")
    all_changes.extend(changes1)
    
    # Step 3: 分类重命名
    logger.info("\n[Step 3] 分类重命名...")
    df, count3, changes3 = apply_category_rename(df)
    logger.info(f"修改 {count3} 条")
    all_changes.extend(changes3)
    
    # Step 4: 双分类合并
    logger.info("\n[Step 4] 双分类合并...")
    df, count4, changes4 = apply_dual_category_merge(df)
    logger.info(f"修改 {count4} 条")
    all_changes.extend(changes4)
    
    # 统计
    total_changes = count2 + count1 + count3 + count4
    logger.info(f"\n总计修改: {total_changes} 条")
    
    if dry_run:
        logger.info("\n[DRY RUN] 未保存文件")
        logger.info("修改示例 (前10条):")
        for change in all_changes[:10]:
            logger.info(f"  {change['legal_articles'][:50]}... | {change['old_category']} → {change['new_category']}")
    else:
        # 保存结果
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"\n已保存: {output_file}")
        
        if all_changes:
            df_log = pd.DataFrame(all_changes)
            df_log.to_csv(log_file, index=False, encoding='utf-8')
            logger.info(f"已保存修改日志: {log_file}")
    
    return total_changes


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='任务10：最终法条分类词典修正')
    parser.add_argument('--dry-run', action='store_true', help='预览模式，不保存文件')
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)
