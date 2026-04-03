from pathlib import Path
from src.config import INPUT_FILE, OUTPUT_FILE
from src.ingestion import load_data, validate_columns, clean_data
from src.scorer import score_candidate
from src.ranker import rank_candidates, generate_reason
from src.logger import init_db, log_interaction
from src.learner import analyze_patterns

def main():
    print("Processing candidates...")
    
    init_db()
    
    df = load_data(INPUT_FILE)
    validate_columns(df)
    df = clean_data(df)
    
    scores = []
    reasons = []
    
    for _, row in df.iterrows():
        score, reason = score_candidate(row)
        scores.append(score)
        reasons.append(reason)
    
    df["score"] = scores
    df["reason"] = reasons
    
    df = rank_candidates(df)
    df["reason"] = df.apply(generate_reason, axis=1)
    
    output_cols = ["name", "score", "tier", "reason"]
    if "email" in df.columns:
        df = df[["name", "email", "score", "tier", "reason"]]
    else:
        df = df[output_cols]
    
    Path(OUTPUT_FILE).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUTPUT_FILE, index=False)
    
    for _, row in df.iterrows():
        score_val = row.get("score", 0)
        try:
            score_int = int(score_val) if score_val is not None else 0
        except (ValueError, TypeError):
            score_int = 0
        
        log_interaction(
            row.get("name", ""),
            row.get("email", ""),
            score_int,
            row.get("tier", ""),
            row.get("reason", "")
        )
    
    print(f"Scoring completed.")
    print(f"Ranking completed.")
    print(f"Output saved to {OUTPUT_FILE}")
    print("Logs updated.")
    
    if len(df) >= 10:
        analysis = analyze_patterns()
        print(f"\nLearning Analysis: {analysis}")

if __name__ == "__main__":
    main()