# 任务9：法条分类词典修正处理

## 概述

根据 `Correction on Mapping from violated law to violation_categories.md` 进行法条分类修正，包含两个子任务：
- **(1-4)** 分类修正：重命名、拆分、关键词覆盖
- **(1-5)** 恢复条目：从 removed_entries.csv 恢复符合关键词的法条

---

## 生成的 CSV 文件说明

### 1. `去掉法条左右多余信息_corrected.csv`

**来源**: 任务9-4 分类修正  
**行数**: 24,177 行  
**说明**: 对原始词典应用分类修正规则后的结果

| 列名 | 说明 |
|-----|-----|
| `legal_articles` | 法条文本 |
| `legal_violation_categories` | 修正后的分类 |
| `violation_keywords` | 匹配的关键词 |
| `is_generic` | 是否为通用法条 |
| `before_legal_categories` | 修正前的分类（如有变化） |
| `reason_ai` | AI 标注理由 |
| `original_big_category` | 原始大类 |

---

### 2. `correction_log.csv`

**来源**: 任务9-4 分类修正  
**行数**: 2,763 行  
**说明**: 记录所有分类变更的日志

| 列名 | 说明 |
|-----|-----|
| `legal_articles` | 法条文本 |
| `old_category` | 原分类 |
| `new_category` | 新分类 |
| `rule_applied` | 应用的规则 |

---

### 3. `recovered_entries.csv`

**来源**: 任务9-5 恢复条目  
**行数**: 566 行  
**说明**: 从 removed_entries.csv 恢复的法条（已清洗、去重）

| 列名 | 说明 |
|-----|-----|
| `legal_articles` | 清洗后的法条文本 |
| `legal_violation_categories` | 根据关键词匹配的分类 |
| `violation_keywords` | 匹配的关键词 |
| `reason_ai` | "从removed恢复: 匹配关键词 xxx" |

---

### 4. `recovered_filtered_out.csv`

**来源**: 任务9-5 恢复条目  
**行数**: 2 行  
**说明**: 被过滤掉的恢复候选（不含书名号或结尾无效）

| 列名 | 说明 |
|-----|-----|
| `legal_articles` | 原始法条 |
| `cleaned_article` | 清洗后的法条 |
| `filter_reason` | 过滤原因 |
| `matched_keyword` | 原本匹配的关键词 |

---

### 5. `去掉法条左右多余信息_final.csv` ⭐

**来源**: 任务9-4 + 任务9-5 合并  
**行数**: 24,736 行  
**说明**: **最终输出的词典**，包含修正后的分类 + 恢复的条目

结构同 `去掉法条左右多余信息_corrected.csv`

---

## 使用方法

```bash
# 任务9-4：分类修正
python correct_category_mapping.py --dry-run  # 预览
python correct_category_mapping.py            # 执行

# 任务9-5：恢复条目
python recover_removed_entries.py --dry-run   # 预览
python recover_removed_entries.py             # 执行
```

---

## 执行统计

### 任务9-4 (分类修正)

| 规则 | 修改数量 |
|-----|---------|
| 分类拆分 | 1200 |
| 重命名 | 1108 |
| 关键词覆盖 | 379 |
| 双分类优先级 | 76 |
| **合计** | **2763** |

### 任务9-5 (恢复条目)

| 步骤 | 数量 |
|-----|-----|
| 关键词匹配 | 682 |
| 清洗修改 | 152 |
| 过滤-无书名号 | 1 |
| 过滤-无效结尾 | 1 |
| 自身去重 | 680 → 566 |
| **最终恢复** | **566** |
