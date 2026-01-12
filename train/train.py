import pandas as pd
import torch
from datasets import Dataset
from setfit import SetFitModel, SetFitTrainer
from sentence_transformers.losses import CosineSimilarityLoss

# ==========================================
# GPU 检测
# ==========================================
print(f"CUDA可用: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"GPU设备: {torch.cuda.get_device_name(0)}")
else:
    print("警告: 未检测到GPU，将使用CPU训练（速度较慢）")

# ==========================================
# 第一步：准备你的“小样本”数据 (训练集)
# ==========================================
# 文件路径 (请确保路径正确，如果是 Windows 建议用 r'')
file_path = r'D:\application\illegal\new-illgal-train\ai_prediction_results_all_samples_merged_v2.csv'

print(f"正在读取文件: {file_path}")

# --- 1. 健壮的读取逻辑 (处理编码和分隔符) ---
df = None
# 常用中文编码列表，按顺序尝试
encodings_to_try = ['utf-8', 'gbk', 'gb18030', 'utf-8-sig'] 

for encoding in encodings_to_try:
    try:
        print(f"尝试使用 {encoding} 编码读取...")
        # 读取 CSV (逗号分隔), 显式指定编码
        df = pd.read_csv(
            file_path, 
            usecols=['vc_id', 'text_combined', 'isneedai'],
            encoding=encoding
        )
        print(f"成功使用 {encoding} 编码读取！")
        break # 读取成功，跳出循环
    except UnicodeDecodeError:
        print(f"编码 {encoding} 解码失败，尝试下一个...")
    except Exception as e:
        # 其他错误 (如文件不存在, 列名不对等) 直接抛出
        print(f"读取发生其他错误: {e}")
        exit()

if df is None:
    print("错误：所有编码尝试均失败，请检查文件格式。")
    exit()

# --- 2. 数据清洗 ---
# 重命名列
df = df.rename(columns={'text_combined': 'text', 'isneedai': 'label'})

# 过滤空标签
df = df.dropna(subset=['label'])

# 确保 label 是整数 (0/1)
try:
    df['label'] = df['label'].astype(int)
except ValueError:
    print("错误：'isneedai' 列包含无法转换为整数的字符，请检查数据。")
    print("非数字值示例:", df[pd.to_numeric(df['label'], errors='coerce').isna()]['label'].head())
    exit()

# 过滤空文本 (text 列如果是 NaN 会导致模型报错)
df = df.dropna(subset=['text'])
df['text'] = df['text'].astype(str) # 确保是字符串类型

# --- 关键修改：打印数据预览 ---
print("-" * 50)
print("【数据预览】请检查中文是否正常显示：")
print("-" * 50)
# 打印前 5 行，展示 ID、标签和文本的前 50 个字
for index, row in df.head(5).iterrows():
    # 标签含义
    label_meaning = "需AI" if row['label'] == 1 else "免AI"
    # 文本去换行符并截断
    clean_text = row['text'].replace('\n', ' ')[:50]
    print(f"ID: {row['vc_id']} | 标签: {row['label']} ({label_meaning}) | 文本: {clean_text}...")
print("-" * 50)

print(f"数据准备就绪: {len(df)} 条样本")
print("标签分布:\n", df['label'].value_counts())

# 转换为 Dataset
dataset = Dataset.from_pandas(df[['text', 'label']])

# ==========================================
# 第二步：加载模型 & 训练
# ==========================================
# 使用更轻量的多语言模型，适合GTX 1060
print("\n正在加载基础模型 paraphrase-multilingual-MiniLM-L12-v2 ...")
model = SetFitModel.from_pretrained("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")

print("开始训练...")
# GTX 1060 6GB 显存有限，使用保守参数
batch_size = 16
num_iterations = 20  # 减少配对数量，加速训练
print(f"训练参数: batch_size={batch_size}, num_iterations={num_iterations}")

trainer = SetFitTrainer(
    model=model,
    train_dataset=dataset,
    loss_class=CosineSimilarityLoss,
    batch_size=batch_size,
    num_iterations=num_iterations,
    num_epochs=1,
    column_mapping={"text": "text", "label": "label"}
)

trainer.train()
print("训练完成！")

# ==========================================
# 第三步：保存模型
# ==========================================
save_path = "./my_ai_necessity_classifier"
model.save_pretrained(save_path)
print(f"模型已保存到: {save_path}")

# ==========================================
# 第四步：验证 (测试中文输出)
# ==========================================
print("\n--- 验证预测效果 ---")
test_samples = df.sample(min(5, len(df)), random_state=42) # 随机抽 5 条
test_texts = test_samples['text'].tolist()
true_labels = test_samples['label'].tolist()

preds = model.predict(test_texts)

for text, pred, true_label in zip(test_texts, preds, true_labels):
    # 简单的格式化输出，方便查看
    res = "✅" if pred == true_label else "❌"
    p_tag = "【需AI】" if pred == 1 else "【免AI】"
    t_tag = "【需AI】" if true_label == 1 else "【免AI】"
    
    # 截取文本前 30 个字，防止刷屏
    short_text = text[:30].replace('\n', ' ') 
    print(f"{res} 预测:{p_tag} (真:{t_tag}) | 文本: {short_text}...")