import pandas as pd
import re

# 6-1 食品药品分类归并
FOOD_DRUG_COLLAPSE_DICT = {
    "食品药品||交通运输违规||安全生产": "食品药品",
    "食品药品||产品质量": "食品药品",
    "食品药品||医疗卫生": "食品药品",
    "食品药品||安全生产": "食品药品",
    "食品药品||安全生产/危化品||安全生产": "食品药品",
    "食品药品||安全生产||产品质量": "食品药品",
    "食品药品||安全生产||医疗卫生": "食品药品",
    "食品药品||无照经营/登记问题": "食品药品",
    "食品药品||消防安全": "食品药品",
    "食品药品||环境保护": "食品药品",
    "食品药品||环境保护||安全生产": "食品药品",
    "食品药品||环境保护||建设工程": "食品药品",
    "未年检登记||食品药品": "食品药品",
    "食品安全": "食品药品"
}

# 6-2 其他多分类修正
OTHER_COLLAPSE_DICT = {
    "安全生产/危化品||环境保护": "环境保护",
    "规范直销和打击传销": "规范直销/打击传销",
    "金融/信贷违规||产品质量": "金融/信贷违规",
    "水资源": "环境保护",
    "税收违规||交通运输违规": "税收违规",
    "海事安全||安全生产||交通运输违规": "海事安全",
    "房屋建筑使用安全": "建筑使用安全",
    "消费者权益纠纷": "消费者权益/市场秩序"
}

def count_categories(category_str):
    """
    计算分类字符串中包含多少个分类（用"||"分隔）
    """
    if pd.isna(category_str):
        return 0
    return len(str(category_str).split("||"))

def fix_categories(input_file, output_file):
    """
    修正分类并过滤多分类词条
    """
    print(f"正在读取文件: {input_file}")
    
    # 读取CSV文件
    df = pd.read_csv(input_file)
    print(f"原始数据行数: {len(df)}")
    
    # 显示原始多分类分布
    print("\n原始分类数量分布:")
    category_counts = df['legal_violation_categories'].apply(count_categories)
    for i in range(1, 6):
        count = (category_counts == i).sum()
        if count > 0:
            print(f"  {i}个分类: {count}条记录")
    
    # 显示3个及以上分类的示例
    multi_category = df[category_counts >= 3]
    print(f"\n含有3个或更多分类的记录数: {len(multi_category)}")
    if len(multi_category) > 0:
        print("示例:")
        for _, row in multi_category.head(5).iterrows():
            print(f"  {row['legal_violation_categories']}")
    
    # 6-1 应用食品药品归并
    print(f"\n应用食品药品归并规则...")
    food_drug_before = df[df['legal_violation_categories'].isin(FOOD_DRUG_COLLAPSE_DICT.keys())].shape[0]
    print(f"需要归并的食品药品记录: {food_drug_before}")
    
    df['legal_violation_categories'] = df['legal_violation_categories'].replace(FOOD_DRUG_COLLAPSE_DICT)
    
    # 6-2 应用其他修正
    print(f"\n应用其他分类修正规则...")
    other_before = df[df['legal_violation_categories'].isin(OTHER_COLLAPSE_DICT.keys())].shape[0]
    print(f"需要修正的其他记录: {other_before}")
    
    df['legal_violation_categories'] = df['legal_violation_categories'].replace(OTHER_COLLAPSE_DICT)
    
    # 6-3 过滤掉含有3个或更多分类的词条
    print(f"\n过滤含有3个或更多分类的词条...")
    
    # 重新计算分类数量
    category_counts_after = df['legal_violation_categories'].apply(count_categories)
    
    # 显示修正后的分布
    print("\n修正后分类数量分布:")
    for i in range(1, 6):
        count = (category_counts_after == i).sum()
        if count > 0:
            print(f"  {i}个分类: {count}条记录")
    
    # 过滤掉3个及以上分类的记录
    df_filtered = df[category_counts_after < 3].copy()
    
    removed_count = len(df) - len(df_filtered)
    print(f"\n移除的含有3个或更多分类的记录数: {removed_count}")
    print(f"最终保留的记录数: {len(df_filtered)}")
    
    # 显示最终分类分布
    print("\n最终分类分布（前20个）:")
    final_counts = df_filtered['legal_violation_categories'].value_counts()
    for category, count in final_counts.head(20).items():
        print(f"  {category}: {count}")
    
    # 保存结果
    df_filtered.to_csv(output_file, index=False, encoding='utf-8')
    print(f"\n处理完成，结果已保存到: {output_file}")
    
    return df_filtered

if __name__ == "__main__":
    input_file = "orginal_remapped_cleaned_group_sorted_ai_labeled_big_groups.csv"
    output_file = "fixed_filtered_categories.csv"
    
    try:
        result_df = fix_categories(input_file, output_file)
        print("处理成功完成！")
    except Exception as e:
        print(f"处理过程中出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
