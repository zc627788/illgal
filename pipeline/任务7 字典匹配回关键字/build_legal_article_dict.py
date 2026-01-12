# -*- coding: utf-8 -*-
"""
任务7：字典匹配回关键字
功能：
1. 使用关键词字典优先匹配法条分类
2. 清理不准确的AI分类
3. 输出清洗后词典和删除词条追溯文件
"""

import pandas as pd
import re
import os

# ============================================================
# 关键词字典 (1-1) + (1-2) + (1-3) 合并
# ============================================================
KEYWORD_DICT = {
    # (1-1) 基础关键词
    "登记管理": "无照经营/登记问题",
    "经营许可证": "无照经营/登记问题",
    "夜间作业许可证": "无照经营/登记问题",
    "商事登记": "无照经营/登记问题",
    "工业产品生产许可证": "无照经营/登记问题",
    "资产负债表": "会计/账务",
    "损益表": "会计/账务",
    "资产评估报告书": "会计/账务",
    "现金支付报销单": "会计/账务",
    "质量认证": "产品质量",
    "卫生许可": "卫生健康",
    "农产品质量安全法": "食品药品",
    "无公害农产品证书": "食品药品",
    "化妆品卫生标准": "食品药品",
    "饼干卫生标准": "食品药品",
    "供水卫生许可证": "食品药品",
    "煤炭经营许可证": "安全生产",
    "市场巡查": "消费者权益/市场秩序",
    "消费者权益": "消费者权益/市场秩序",
    "商品房买卖合同": "房地产/土地",
    "商品房预售许可证": "房地产/土地",
    "房屋租赁合同": "房地产/土地",
    "建筑材料放射性核素限量": "安全生产",
    "信息网络传播视听节目许可证": "公共文化与传媒",
    "广播电视": "公共文化与传媒",
    "视频点播": "公共文化与传媒",
    "公路法": "交通运输违规",
    "公路安全": "交通运输违规",
    "定量包装商品计量监督管理办法": "计量/器具",
    "产品回收函": "产品质量",
    "网络交易": "网络市场交易/市场秩序",
    "快递市场管理办法": "网络市场交易/市场秩序",
    "企业信息公示暂行条例": "企业信息公示",
    "城市公交": "交通运输违规",
    "中华人民共和国统计法": "统计相关",
    "城乡规划": "建设工程",
    "娱乐经营许可证": "治安管理",
    "固体废物进口管理办法": "环境保护",
    "环境保护": "环境保护",
    "市容和环境卫生": "环境保护",
    "招标投标法": "工程建设/招投标",
    "海关法": "海关/进出口",
    "反洗钱法": "金融/信贷违规",
    "房屋建筑使用安全": "建筑使用安全",
    "内河交通安全": "海事安全",
    "集中申报": "反垄断",
    "滥用市场支配地位": "反垄断",
    "限制竞争": "反垄断",
    "垄断": "反垄断",
    "供热采暖": "建筑使用安全",
    "户外广告登记": "虚假广告/虚假宣传",
    "网络安全": "网络/数据安全",
    "保险法": "金融/信贷违规",
    "假冒伪劣商品": "产品质量",
    "城市建筑垃圾": "建设工程",
    "保险专业代理机构监管规定": "金融/信贷违规",
    "无线电管理条例": "通讯",
    "食品安全": "食品药品",
    "消防法": "消防安全",
    "产品法": "产品质量",
    "恐怖主义": "反恐",
    
    # (1-2) Additional mapping
    "消费者投诉": "消费者权益/市场秩序",
    "专项审计": "会计/账务",
    "城市容貌": "环境保护",
    "审计法": "会计/账务",
    "标准化法": "产品质量",
    
    # (1-3) 2025/12/23 新增
    "金融统计管理规定": "统计相关",
    "统计执法监督检查办法": "统计相关",
    "供热采暖管理办法": "建筑使用安全",
    "生产和销售假冒伪劣商品": "产品质量",
    "印刷业管理条例": "公共文化与传媒",
    "消毒管理办法": "医疗卫生",
    "记账凭证": "会计/账务",
    "凭证": "会计/账务",
    "垃圾分类": "环境保护",
    "生活垃圾": "环境保护",
    "审计": "会计/账务",
    "个体地址企业法": "市场主体与登记治理",
    "防空法": "公共安全与社会治理",
    "政府采购": "工程建设/招投标",
    "水土保持法": "环境保护",
    "野生动物保护法": "环境保护",
    "中国药典": "食品药品",
    "反不正当竟争法": "不正当竞争/商业贿赂",
    "种子法": "农业",
    "价格法": "价格/收费",
    "动物防疫法": "动物防疫",
    "国家标准": "产品质量与标准认证",
    "GB9694-88": "产品质量与标准认证",
    "农业农村": "农业",
    "农业法": "农业",
    "农民专业合作社法": "农业",
    "出境入境": "海关/进出口",
    "中国共产党纪律处分": "党纪政务处分",
    "城市市容": "环境保护",
    "医药有限公司": "食品药品",
    "价格违法": "价格/收费",
    "住房公积金管理": "住房公积金管理",
    "农药": "食品药品",
    "动物检疫": "食品药品",
    "卫生标准": "卫生健康",
    "化妆品": "食品药品",
    "门前三包": "环境保护",
    "中药": "食品药品",
    "住房租赁": "房地产/土地",
    "农业": "农业",
    "垃圾": "环境保护",
    "医药": "食品药品",
    "食品": "食品药品",
    "饲料质量": "食品药品",
    "饼干卫生": "食品药品",
    "税": "税收违规",
    "煤矿": "安全生产",
    "自然资源违法": "资源监管",
    "藥商許可執照": "食品药品",
    "肥料": "食品药品",
    "污染": "环境保护",
    "价格欺诈": "价格/收费",
    "价格": "价格/收费",
    "招标投标": "招投标",
    "居住证条例": "流动人口管理",
    "流动人口": "流动人口管理",
    "劳动监察": "劳动保障/用工",
    "游泳场所": "公共安全与社会治理",
    "物业管理": "建筑使用安全",
    "治安管理": "公共安全与社会治理",
    "加班": "劳动保障/用工",
    "市容": "环境保护",
    "传销": "规范直销/打击传销",
    "投机倒把": "规范直销/打击传销",
    "消费纠纷": "消费者权益",
    "虚报统计材料": "统计相关",
    "供热设施安全": "建筑使用安全",
    "饮用水": "食品药品",
    "绿化": "环境保护",
    "建筑工程施工许可证": "建设工程",
    "进出口": "海关/进出口",
    "出入境": "海关/进出口",
    "投标": "招投标",
    "拍卖监督": "市场秩序与竞争监管",
    "毒化学": "安全生产/危化品",
    "易制爆化学": "安全生产/危化品",
    "价目表": "价格/收费",
    "未成年工": "劳动保障/用工",
    "童工": "劳动保障/用工",
    "河道建设": "海事安全",
    "城市供水": "食品药品",
    "饲料": "食品药品",
    "物价局": "价格/收费",
    "电力设施": "电力",
    "电力法": "电力",
    "供电合同": "电力",
    "供用电合同": "电力",
    "供用电": "电力",
    "电力": "电力",
    "无线电": "通讯",
    "卫星": "通讯",
    "收费管理办法": "价格/收费",
    "促销": "市场秩序与竞争监管",
    "乘客": "交通运输违规",
    "医疗": "卫生健康",
    "城市公共空间": "城市治理与公共服务",
    "市政设施管理": "城市治理与公共服务",
    "广告法": "虚假广告/虚假宣传",
    "餐饮": "食品药品",
    "税收征收管理法": "税收违规",
    "不正当竞争": "不正当竞争/商业贿赂",
    "烟草": "烟草",
    "从业资格证": "劳动保障/用工",
    "电梯": "特种设备",
    "人力资源和社会保障局": "劳动保障/用工",
    "道路交通安全法": "交通运输违规",
    "土地管理法": "房地产/土地",
    "民用航空": "交通运输违规",
    "通航安全": "交通运输违规",
    "特种设备": "特种设备",
    "网络安全法": "网络安全",
    "职业病": "劳动保障/用工",
    "船舶安全": "海事安全",
    "药品": "食品药品",
    "农产品": "食品药品",
    "计算机信息系统安全": "网络安全",
    "运输": "交通运输违规",
    "防治船舶污染内河水域": "环境保护",
    "商品房买卖": "消费者权益/市场秩序",
    "建筑垃圾": "环境保护",
    "快递": "交通运输违规",
    "道路危险货物运输": "交通运输违规",
    "港口危险货物安全": "海事安全",
    "登记": "无照经营/登记问题",  # 放在最后，因为比较通用
}

# ============================================================
# (6-4) 特定法条分类覆盖
# ============================================================
OVERRIDE_DICT = {
    "<<中华人民共和国公司法>>第二百零一条": "市场主体与登记治理",
    "《中华人民共和国不动产权证书》": "房地产/土地",
    "《中华人民共和国公司法》第二百一十一条": "股东利润分配",
}

# ============================================================
# (6-5) 泛型法条删除规则（正则模式）
# ============================================================
GENERIC_PATTERNS = [
    (r"^<<中华人民共和国公司法>>$", "公司法本身太泛"),
    (r"行政处罚程序", "程序性，不含实体违规"),
    (r"年度报告", "报告书类"),
    (r"行政处罚自由裁量权", "程序性"),
    (r"行政处罚裁量权", "程序性"),
    (r"可以.*罚款", "处罚措施描述"),
    (r"加处.*罚款", "处罚措施描述"),
    (r"处以.*罚款", "处罚措施描述"),
]


def check_no_book_quote(legal_article):
    """
    检查是否符合(6-8)删除规则：法条不含书名号（《》、<< >>）
    返回: (是否删除, 删除原因)
    """
    if pd.isna(legal_article):
        return True, "(6-8) 法条为空"
    
    article_str = str(legal_article)
    # 截取法条前50字符用于展示
    article_preview = article_str[:50] + "..." if len(article_str) > 50 else article_str
    
    # 检查是否包含书名号
    has_book_quote = (
        "《" in article_str or 
        "》" in article_str or 
        "<<" in article_str or 
        ">>" in article_str
    )
    
    if not has_book_quote:
        return True, f"(6-8) 法条不含书名号 | 法条: {article_preview}"
    
    return False, None


def check_invalid_ending(legal_article):
    """
    检查是否符合(6-9)删除规则：法条结尾无效
    有效结尾：》、条、款、项、号、规定、办法、细则、条例、标准、通知、意见、决定
    返回: (是否删除, 删除原因)
    """
    if pd.isna(legal_article):
        return False, None  # 空值由其他规则处理
    
    article_str = str(legal_article).strip()
    if not article_str:
        return False, None
    
    # 截取法条前50字符用于展示
    article_preview = article_str[:50] + "..." if len(article_str) > 50 else article_str
    
    # 有效的结尾模式
    valid_endings = (
        '》', '>', '＞',           # 书名号结尾
        '条', '款', '项',         # 法条编号结尾
        '号',                     # 文号结尾
        '规定', '办法', '细则', '条例', '标准',  # 法规名称结尾
        '通知', '意见', '决定', '规则', '规程',  # 文件类型结尾
        '解释', '批复', '答复',   # 司法文件结尾
    )
    
    # 检查是否以有效模式结尾
    if article_str.endswith(valid_endings):
        return False, None
    
    # 获取最后一个字符，用于原因说明
    last_chars = article_str[-5:] if len(article_str) >= 5 else article_str
    return True, f"(6-9) 法条结尾无效'{last_chars}' | 法条: {article_preview}"


def get_script_dir():
    """获取脚本所在目录"""
    return os.path.dirname(os.path.abspath(__file__))


def build_sorted_keywords():
    """按关键词长度降序排序，优先匹配更具体的关键词"""
    sorted_items = sorted(KEYWORD_DICT.items(), key=lambda x: len(x[0]), reverse=True)
    return sorted_items


def match_keyword(legal_article, sorted_keywords):
    """
    匹配法条到关键词
    返回: (匹配到的分类, 匹配的关键词) 或 (None, None)
    """
    if pd.isna(legal_article):
        return None, None
    
    article_str = str(legal_article)
    for keyword, category in sorted_keywords:
        if keyword in article_str:
            return category, keyword
    return None, None


def check_generic_removal(legal_article):
    """
    检查是否符合(6-5)泛型法条删除规则
    返回: (是否删除, 删除原因)
    """
    if pd.isna(legal_article):
        return False, None
    
    article_str = str(legal_article)
    # 截取法条前50字符用于展示
    article_preview = article_str[:50] + "..." if len(article_str) > 50 else article_str
    
    for pattern, reason in GENERIC_PATTERNS:
        match = re.search(pattern, article_str)
        if match:
            matched_text = match.group(0)
            return True, f"(6-5) {reason} | 匹配模式: '{matched_text}' | 法条: {article_preview}"
    return False, None


def check_star_removal(category, legal_article=None):
    """
    检查是否符合(6-6)删除规则：分类含星号（AI不确定分类）
    注意：'其他违法行为'和'其他'分类保留，不删除
    返回: (是否删除, 删除原因)
    """
    if pd.isna(category):
        return False, None
    
    cat_str = str(category)
    
    # 截取法条前50字符用于展示
    article_preview = ""
    if legal_article and not pd.isna(legal_article):
        article_str = str(legal_article)
        article_preview = article_str[:50] + "..." if len(article_str) > 50 else article_str
    
    # 只检查星号分类（'其他'分类保留）
    if "*" in cat_str:
        return True, f"(6-6) AI分类含星号'{cat_str}'，分类不确定 | 法条: {article_preview}"
    
    return False, None


def check_generic_with_specific_category(before_cat, current_cat, legal_article=None):
    """
    检查是否符合(6-7)删除规则：泛型法条被AI分为具体分类
    返回: (是否删除, 删除原因)
    """
    if pd.isna(before_cat) or pd.isna(current_cat):
        return False, None
    
    before_str = str(before_cat)
    current_str = str(current_cat)
    
    # 截取法条前50字符用于展示
    article_preview = ""
    if legal_article and not pd.isna(legal_article):
        article_str = str(legal_article)
        article_preview = article_str[:50] + "..." if len(article_str) > 50 else article_str
    
    # 检查是否为泛型法条
    if "<泛类型>" in before_str:
        # 检查当前分类是否为具体分类（非"其他"）
        if current_str not in ["其他违法行为", "其他"] and "*" not in current_str:
            return True, f"(6-7) 泛型法条被AI分为具体分类'{current_str}'，应删除 | 原标记: {before_str} | 法条: {article_preview}"
    
    return False, None


def process_step1_keyword_matching(df, sorted_keywords):
    """
    Step 1: 关键词优先匹配
    返回: (处理后的df, 匹配数, 已匹配的行索引集合)
    """
    print("\n" + "="*60)
    print("Step 1: 关键词优先匹配")
    print("="*60)
    
    match_count = 0
    matched_indices = set()  # 记录关键词匹配成功的行索引
    
    for idx, row in df.iterrows():
        legal_article = row['legal_articles']
        new_category, matched_keyword = match_keyword(legal_article, sorted_keywords)
        
        if new_category:
            # 保存原分类到 before_legal_categories（直接覆盖，不追加）
            original_cat = row['legal_violation_categories']
            
            # 直接用 (匹配)原分类 覆盖 before_legal_categories
            df.at[idx, 'before_legal_categories'] = f"(匹配){original_cat}"
            
            # 覆盖分类
            df.at[idx, 'legal_violation_categories'] = new_category
            match_count += 1
            matched_indices.add(idx)  # 记录已匹配的索引
    
    print(f"关键词匹配命中数: {match_count}")
    return df, match_count, matched_indices


def process_step2_cleaning(df, matched_indices=None):
    """
    Step 2: 清理不准确的分类
    处理顺序：先特定法条覆盖，再处理泛型法条删除和星号分类删除
    
    Args:
        df: 数据DataFrame
        matched_indices: 关键词匹配成功的行索引集合（豁免6-5规则）
    """
    if matched_indices is None:
        matched_indices = set()
    
    print("\n" + "="*60)
    print("Step 2: 清理不准确的分类")
    print("="*60)
    
    # === 第一阶段：特定法条覆盖 ===
    override_count = 0
    for idx, row in df.iterrows():
        legal_article = row['legal_articles']
        if legal_article in OVERRIDE_DICT:
            df.at[idx, 'legal_violation_categories'] = OVERRIDE_DICT[legal_article]
            override_count += 1
    print(f"(6-4) 特定法条覆盖数: {override_count}")
    
    # === 第二阶段：泛型法条删除和星号分类删除 ===
    removed_entries = []
    keep_indices = []
    
    generic_removal_count = 0
    star_removal_count = 0
    generic_specific_removal_count = 0
    no_book_quote_removal_count = 0
    invalid_ending_removal_count = 0
    
    for idx, row in df.iterrows():
        legal_article = row['legal_articles']
        current_cat = row['legal_violation_categories']
        before_cat = row.get('before_legal_categories', '')
        
        # 检查是否为关键词匹配成功的行（豁免6-5规则）
        is_keyword_matched = idx in matched_indices
        
        # 2.2 (6-5) 移除泛型法条（关键词匹配成功的行豁免）
        if not is_keyword_matched:
            should_remove, reason = check_generic_removal(legal_article)
            if should_remove:
                row_copy = row.copy()
                row_copy['remove_reason'] = reason
                removed_entries.append(row_copy)
                generic_removal_count += 1
                continue
        
        # 2.3 (6-6) 移除含星号分类（'其他'分类保留）
        should_remove, reason = check_star_removal(current_cat, legal_article)
        if should_remove:
            row_copy = row.copy()
            row_copy['remove_reason'] = reason
            removed_entries.append(row_copy)
            star_removal_count += 1
            continue
        
        # 2.4 (6-7) 移除泛型法条被AI分为具体分类的
        should_remove, reason = check_generic_with_specific_category(before_cat, current_cat, legal_article)
        if should_remove:
            row_copy = row.copy()
            row_copy['remove_reason'] = reason
            removed_entries.append(row_copy)
            generic_specific_removal_count += 1
            continue
        
        # 2.5 (6-8) 移除不含书名号的法条（关键词匹配成功的行也不豁免）
        should_remove, reason = check_no_book_quote(legal_article)
        if should_remove:
            row_copy = row.copy()
            row_copy['remove_reason'] = reason
            removed_entries.append(row_copy)
            no_book_quote_removal_count += 1
            continue
        
        # 2.6 (6-9) 移除结尾无效的法条
        should_remove, reason = check_invalid_ending(legal_article)
        if should_remove:
            row_copy = row.copy()
            row_copy['remove_reason'] = reason
            removed_entries.append(row_copy)
            invalid_ending_removal_count += 1
            continue
        
        # 保留
        keep_indices.append(idx)
    
    # 统计输出
    print(f"(6-5) 泛型法条删除数: {generic_removal_count}")
    print(f"(6-6) 星号分类删除数: {star_removal_count}")
    print(f"(6-7) 泛型+具体分类删除数: {generic_specific_removal_count}")
    print(f"(6-8) 无书名号删除数: {no_book_quote_removal_count}")
    print(f"(6-9) 无效结尾删除数: {invalid_ending_removal_count}")
    print(f"总删除数: {len(removed_entries)}")
    
    # 保留的数据
    df_cleaned = df.loc[keep_indices].copy()
    
    # 删除的数据
    df_removed = pd.DataFrame(removed_entries) if removed_entries else pd.DataFrame()
    
    return df_cleaned, df_removed


def main():
    script_dir = get_script_dir()
    
    # 输入输出文件路径
    input_file = os.path.join(script_dir, "任务6_分类已修正.csv")
    output_cleaned = os.path.join(script_dir, "任务7_清洗后词典.csv")
    output_removed = os.path.join(script_dir, "任务7_删除条目.csv")
    output_step1 = os.path.join(script_dir, "任务7_中间_关键词匹配.csv")
    
    print("="*60)
    print("任务7：字典匹配回关键字")
    print("="*60)
    
    # 读取输入文件
    print(f"\n读取文件: {input_file}")
    df = pd.read_csv(input_file)
    print(f"原始数据行数: {len(df)}")
    
    # 构建排序后的关键词列表
    sorted_keywords = build_sorted_keywords()
    print(f"关键词字典大小: {len(sorted_keywords)}")
    
    # Step 1: 关键词优先匹配
    df, match_count, matched_indices = process_step1_keyword_matching(df, sorted_keywords)
    
    # 保存Step1中间结果
    df.to_csv(output_step1, index=False, encoding='utf-8')
    print(f"\nStep1 中间结果已保存: {output_step1}")
    
    # Step 2: 清理不准确的分类（传入匹配索引用于豁免6-5规则）
    df_cleaned, df_removed = process_step2_cleaning(df, matched_indices)
    
    # 保存最终结果
    df_cleaned.to_csv(output_cleaned, index=False, encoding='utf-8')
    print(f"\n清洗后词典已保存: {output_cleaned}")
    print(f"最终保留行数: {len(df_cleaned)}")
    
    if len(df_removed) > 0:
        df_removed.to_csv(output_removed, index=False, encoding='utf-8')
        print(f"删除词条已保存: {output_removed}")
        print(f"删除条目数: {len(df_removed)}")
    else:
        print("无删除条目")
    
    # 统计 (匹配) 标识数量
    match_tag_count = df_cleaned['before_legal_categories'].str.contains(r'\(匹配\)', na=False, regex=True).sum()
    print(f"\nbefore_legal_categories 中含 '(匹配)' 标识的行数: {match_tag_count}")
    
    # 按 legal_violation_categories 排序
    print("\n按 legal_violation_categories 排序...")
    df_cleaned = df_cleaned.sort_values(by='legal_violation_categories').reset_index(drop=True)
    
    # 保存排序后的结果
    df_cleaned.to_csv(output_cleaned, index=False, encoding='utf-8')
    print(f"排序完成，结果已保存")
    
    print("\n" + "="*60)
    print("处理完成！")
    print("="*60)


if __name__ == "__main__":
    main()
