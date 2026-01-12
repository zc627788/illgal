# -*- coding: utf-8 -*-
"""分析法条开头和结尾模式"""
import pandas as pd
from collections import Counter

df = pd.read_csv('task7_cleaned_dict.csv')
articles = df['legal_articles'].dropna().astype(str).str.strip()

# 1. 单字符开头统计
print("=" * 60)
print("1. 单字符开头统计（前20）")
print("=" * 60)
single_start = Counter()
for art in articles:
    if art:
        single_start[art[0]] += 1
for char, count in single_start.most_common(20):
    print(f"  '{char}' : {count}")

# 2. 双字符开头统计
print("\n" + "=" * 60)
print("2. 双字符开头统计（前20）")
print("=" * 60)
double_start = Counter()
for art in articles:
    if len(art) >= 2:
        double_start[art[:2]] += 1
for start, count in double_start.most_common(20):
    print(f"  '{start}' : {count}")

# 3. 三字符开头统计
print("\n" + "=" * 60)
print("3. 三字符开头统计（前20）")
print("=" * 60)
triple_start = Counter()
for art in articles:
    if len(art) >= 3:
        triple_start[art[:3]] += 1
for start, count in triple_start.most_common(20):
    print(f"  '{start}' : {count}")

# 4. 非标准开头样例（不以《或<开头）
print("\n" + "=" * 60)
print("4. 非书名号开头样例（前20条）")
print("=" * 60)
non_standard_start = [art for art in articles if art and not art.startswith(('《', '<', '＜', '〈'))]
print(f"非书名号开头总数: {len(non_standard_start)}")
for art in non_standard_start[:20]:
    preview = art[:70] + "..." if len(art) > 70 else art
    print(f"  [{art[:3]}] {preview}")

# 5. 统计总结
print("\n" + "=" * 60)
print("5. 统计总结")
print("=" * 60)
total = len(articles)
book_quote_start = sum(1 for art in articles if art and art.startswith(('《', '<', '＜', '〈')))
print(f"总法条数: {total}")
print(f"以书名号开头: {book_quote_start} ({book_quote_start/total*100:.1f}%)")
print(f"非书名号开头: {total - book_quote_start} ({(total-book_quote_start)/total*100:.1f}%)")
