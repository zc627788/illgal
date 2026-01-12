"""
任务9：法条分类词典修正处理

根据 Correction on Mapping from violated law to violation_categories.md 的 (1-4) 部分:
1. 分类拆分: 建设工程与房地产 -> 建设工程 / 房地产/土地
2. 分类重命名: 产品质量与安全 -> 产品质量, 等
3. 双分类优先级: 处理 || 分隔的双分类
4. 关键词直接分类: 商业贿赂, 不正当竞争, 广告, 安全生产管理条例
"""

import pandas as pd
from pathlib import Path
import logging
from datetime import datetime

# ============ 配置 ============

# 1. 分类重命名规则
CATEGORY_RENAME = {
    "产品质量与安全": "产品质量",
    "工程建设/招投标": "招投标",
    "交通运输": "交通运输违规",
}

# 2. 双分类优先级处理 (左边优先级低, 保留右边)
# 注意: 需要处理顺序问题, 因为 || 分隔符两边可能顺序不同
DUAL_CATEGORY_PRIORITY = {
    # (低优先级, 高优先级) -> 保留高优先级
    ("侵犯商标/知识产权", "安全生产"): "安全生产",
    ("侵犯商标/知识产权", "环境保护"): "环境保护",
    ("安全生产", "交通运输违规"): "交通运输违规",
    ("安全生产", "医疗卫生"): "医疗卫生",
    ("安全生产", "海事安全"): "海事安全",
    ("网络/数据安全", "安全生产"): "网络/数据安全",
}

# 3. 关键词直接分类 (法条中含有关键词时，直接标记为对应分类)
KEYWORD_CATEGORY_OVERRIDE = {
    "商业贿赂": "不正当竞争/商业贿赂",
    "不正当竞争": "不正当竞争/商业贿赂",
    "广告": "虚假广告/虚假宣传",
    "安全生产管理条例": "安全生产",
}

# ============ 处理函数 ============

def setup_logging(log_dir: Path):
    """配置日志"""
    log_file = log_dir / f"correct_category_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_file, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)


def apply_keyword_override(legal_article: str, current_category: str) -> tuple[str, str]:
    """
    规则1: 关键词直接分类
    法条中含有特定关键词时, 直接覆盖分类
    
    返回: (new_category, rule_applied) 或 (None, None) 如果不适用
    """
    if pd.isna(legal_article):
        return None, None
    
    for keyword, target_category in KEYWORD_CATEGORY_OVERRIDE.items():
        if keyword in legal_article:
            return target_category, f"关键词覆盖: {keyword} -> {target_category}"
    
    return None, None


def apply_construction_realestate_split(legal_article: str, current_category: str) -> tuple[str, str]:
    """
    规则2: 建设工程与房地产 拆分逻辑
    - 法条含 '房地产' 或 '土地' -> 返回 '房地产/土地'
    - 否则 -> 返回 '建设工程'
    
    返回: (new_category, rule_applied) 或 (None, None) 如果不适用
    """
    if current_category != "建设工程与房地产":
        return None, None
    
    if pd.isna(legal_article):
        # 无法判断, 保留原分类改为建设工程
        return "建设工程", "分类拆分: 建设工程与房地产 -> 建设工程 (默认)"
    
    if "房地产" in legal_article or "土地" in legal_article:
        return "房地产/土地", "分类拆分: 建设工程与房地产 -> 房地产/土地"
    else:
        return "建设工程", "分类拆分: 建设工程与房地产 -> 建设工程"


def apply_dual_category_priority(current_category: str) -> tuple[str, str]:
    """
    规则3: 双分类优先级处理
    当分类同时给出两个类别时（以 || 分隔），按规则保留单一分类
    
    返回: (new_category, rule_applied) 或 (None, None) 如果不适用
    """
    if pd.isna(current_category) or "||" not in current_category:
        return None, None
    
    # 尝试拆分双分类
    parts = [p.strip() for p in current_category.split("||")]
    if len(parts) != 2:
        return None, None
    
    cat1, cat2 = parts[0], parts[1]
    
    # 正向匹配
    if (cat1, cat2) in DUAL_CATEGORY_PRIORITY:
        target = DUAL_CATEGORY_PRIORITY[(cat1, cat2)]
        return target, f"双分类优先级: {current_category} -> {target}"
    
    # 反向匹配 (顺序可能不同)
    if (cat2, cat1) in DUAL_CATEGORY_PRIORITY:
        target = DUAL_CATEGORY_PRIORITY[(cat2, cat1)]
        return target, f"双分类优先级: {current_category} -> {target}"
    
    return None, None


def apply_category_rename(current_category: str) -> tuple[str, str]:
    """
    规则4: 分类重命名
    
    返回: (new_category, rule_applied) 或 (None, None) 如果不适用
    """
    if pd.isna(current_category):
        return None, None
    
    if current_category in CATEGORY_RENAME:
        target = CATEGORY_RENAME[current_category]
        return target, f"重命名: {current_category} -> {target}"
    
    return None, None


def process_row(row: pd.Series) -> tuple[str, str]:
    """
    处理单行数据, 按优先级依次应用规则
    
    优先级顺序:
    1. 关键词直接分类 (覆盖)
    2. 建设工程与房地产拆分
    3. 双分类优先级处理
    4. 分类重命名
    
    返回: (new_category, rule_applied) - 如果没有实际变化, rule_applied 为 None
    """
    legal_article = row.get('legal_articles', '')
    current_category = row.get('legal_violation_categories', '')
    
    # 规则1: 关键词直接分类
    new_cat, rule = apply_keyword_override(legal_article, current_category)
    if new_cat is not None and new_cat != current_category:
        return new_cat, rule
    
    # 规则2: 建设工程与房地产拆分
    new_cat, rule = apply_construction_realestate_split(legal_article, current_category)
    if new_cat is not None and new_cat != current_category:
        return new_cat, rule
    
    # 规则3: 双分类优先级
    new_cat, rule = apply_dual_category_priority(current_category)
    if new_cat is not None and new_cat != current_category:
        return new_cat, rule
    
    # 规则4: 分类重命名
    new_cat, rule = apply_category_rename(current_category)
    if new_cat is not None and new_cat != current_category:
        return new_cat, rule
    
    # 无变化
    return current_category, None


def main(dry_run: bool = False):
    """主处理函数"""
    script_dir = Path(__file__).parent
    input_file = script_dir / "去掉法条左右多余信息.csv"
    output_file = script_dir / "去掉法条左右多余信息_corrected.csv"
    log_file = script_dir / "correction_log.csv"
    
    logger = setup_logging(script_dir)
    logger.info(f"开始处理: {input_file}")
    
    # 读取数据
    df = pd.read_csv(input_file, encoding='utf-8')
    logger.info(f"读取 {len(df)} 行数据")
    
    # 处理每一行
    changes = []
    for idx, row in df.iterrows():
        old_category = row['legal_violation_categories']
        new_category, rule_applied = process_row(row)
        
        if rule_applied is not None:
            changes.append({
                'legal_articles': row['legal_articles'],
                'old_category': old_category,
                'new_category': new_category,
                'rule_applied': rule_applied
            })
            
            if not dry_run:
                df.at[idx, 'legal_violation_categories'] = new_category
    
    # 统计
    logger.info(f"共修改 {len(changes)} 行")
    
    # 按规则分类统计
    rule_stats = {}
    for change in changes:
        rule_type = change['rule_applied'].split(':')[0]
        rule_stats[rule_type] = rule_stats.get(rule_type, 0) + 1
    
    logger.info("规则统计:")
    for rule, count in sorted(rule_stats.items(), key=lambda x: -x[1]):
        logger.info(f"  {rule}: {count}")
    
    if dry_run:
        logger.info("[DRY RUN] 未保存任何文件")
        # 输出前10条修改示例
        logger.info("修改示例 (前10条):")
        for change in changes[:10]:
            logger.info(f"  {change['old_category']} -> {change['new_category']} ({change['rule_applied']})")
    else:
        # 保存修正后的文件
        df.to_csv(output_file, index=False, encoding='utf-8')
        logger.info(f"已保存修正后文件: {output_file}")
        
        # 保存修改日志
        if changes:
            log_df = pd.DataFrame(changes)
            log_df.to_csv(log_file, index=False, encoding='utf-8')
            logger.info(f"已保存修改日志: {log_file}")
    
    return len(changes)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='法条分类词典修正处理')
    parser.add_argument('--dry-run', action='store_true', help='仅统计, 不保存文件')
    args = parser.parse_args()
    
    main(dry_run=args.dry_run)
