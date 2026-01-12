"""
Prediction Script - Use Trained SetFit Model to Predict isNeedAI
使用训练好的 SetFit 模型预测文档是否需要AI处理 (0=规则处理, 1=需要AI)

Usage:
    python predict.py --input <input.csv> --output <output.csv>
"""

import argparse
import pandas as pd
import os
from setfit import SetFitModel

# ==========================================
# Configuration
# ==========================================
DEFAULT_MODEL_PATH = "./my_ai_necessity_classifier"
DEFAULT_INPUT_COLUMN = "text_combined"
DEFAULT_OUTPUT_COLUMN = "need_ai"
BATCH_SIZE = 32  # Batch size for prediction

# ==========================================
# Prediction Functions
# ==========================================

def load_model(model_path: str) -> SetFitModel:
    """Load trained SetFit model from local path"""
    if not os.path.exists(model_path):
        raise FileNotFoundError(f"Model not found at: {model_path}")
    
    print(f"Loading model from: {model_path}")
    model = SetFitModel.from_pretrained(model_path)
    print("Model loaded successfully!")
    return model


def predict_batch(model: SetFitModel, texts: list) -> list:
    """Predict isNeedAI for a batch of texts"""
    predictions = model.predict(texts)
    return [int(p) for p in predictions]


def process_csv(
    input_file: str,
    output_file: str,
    model_path: str = DEFAULT_MODEL_PATH,
    text_column: str = DEFAULT_INPUT_COLUMN,
    output_column: str = DEFAULT_OUTPUT_COLUMN
):
    """
    Process CSV file and predict isNeedAI for each record
    
    Args:
        input_file: Path to input CSV
        output_file: Path to output CSV
        model_path: Path to trained model directory
        text_column: Column name containing text to classify
        output_column: Column name for prediction output
    """
    # Load model
    model = load_model(model_path)
    
    # Read input CSV
    print(f"Reading input file: {input_file}")
    encodings = ['utf-8', 'utf-8-sig', 'gbk', 'gb18030']
    df = None
    
    for enc in encodings:
        try:
            df = pd.read_csv(input_file, encoding=enc)
            print(f"Successfully read with encoding: {enc}")
            break
        except UnicodeDecodeError:
            continue
    
    if df is None:
        raise ValueError("Failed to read CSV with all attempted encodings")
    
    print(f"Total records: {len(df)}")
    
    # Validate text column exists
    if text_column not in df.columns:
        raise ValueError(f"Column '{text_column}' not found in CSV. Available columns: {list(df.columns)}")
    
    # Prepare texts (handle NaN values)
    df[text_column] = df[text_column].fillna("").astype(str)
    texts = df[text_column].tolist()
    
    # Batch prediction
    print(f"Starting prediction with batch size {BATCH_SIZE}...")
    all_predictions = []
    
    for i in range(0, len(texts), BATCH_SIZE):
        batch = texts[i:i + BATCH_SIZE]
        batch_preds = predict_batch(model, batch)
        all_predictions.extend(batch_preds)
        
        # Progress indicator
        progress = min(i + BATCH_SIZE, len(texts))
        print(f"Processed: {progress}/{len(texts)} ({progress/len(texts)*100:.1f}%)")
    
    # Add predictions to DataFrame
    df[output_column] = all_predictions
    
    # Save results
    df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Results saved to: {output_file}")
    
    # Statistics
    need_ai_count = sum(all_predictions)
    no_ai_count = len(all_predictions) - need_ai_count
    print(f"\n=== Prediction Statistics ===")
    print(f"Total records: {len(all_predictions)}")
    print(f"Need AI (1): {need_ai_count} ({need_ai_count/len(all_predictions)*100:.1f}%)")
    print(f"No AI (0): {no_ai_count} ({no_ai_count/len(all_predictions)*100:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Predict isNeedAI using trained SetFit model"
    )
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Input CSV file path"
    )
    parser.add_argument(
        "--output", "-o",
        required=True,
        help="Output CSV file path"
    )
    parser.add_argument(
        "--model", "-m",
        default=DEFAULT_MODEL_PATH,
        help=f"Path to trained model (default: {DEFAULT_MODEL_PATH})"
    )
    parser.add_argument(
        "--text-column", "-t",
        default=DEFAULT_INPUT_COLUMN,
        help=f"Text column name (default: {DEFAULT_INPUT_COLUMN})"
    )
    parser.add_argument(
        "--output-column", "-c",
        default=DEFAULT_OUTPUT_COLUMN,
        help=f"Output column name (default: {DEFAULT_OUTPUT_COLUMN})"
    )
    
    args = parser.parse_args()
    
    process_csv(
        input_file=args.input,
        output_file=args.output,
        model_path=args.model,
        text_column=args.text_column,
        output_column=args.output_column
    )


if __name__ == "__main__":
    main()
