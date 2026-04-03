import pandas as pd
from pathlib import Path

REQUIRED_COLUMNS = ["name", "email", "skills", "github", "answer", "response_time"]

def load_data(file_path):
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    if path.suffix == ".csv":
        df = pd.read_csv(path)
    elif path.suffix in [".xlsx", ".xls"]:
        df = pd.read_excel(path)
    else:
        raise ValueError(f"Unsupported file format: {path.suffix}")
    
    return df

def validate_columns(df):
    missing = [col for col in REQUIRED_COLUMNS if col not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")
    return True

def normalize_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip().lower()

def clean_data(df):
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == "object":
            df[col] = df[col].apply(normalize_text)
    df = df.fillna("")
    return df