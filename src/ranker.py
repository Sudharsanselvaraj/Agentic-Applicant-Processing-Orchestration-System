from src.config import TIER_THRESHOLDS

def rank_candidates(df):
    df = df.copy()
    
    if "score" not in df.columns:
        raise ValueError("Score column missing from dataframe")
    
    df["tier"] = df["score"].apply(get_tier)
    df = df.sort_values("score", ascending=False).reset_index(drop=True)
    return df

def get_tier(score):
    if score >= TIER_THRESHOLDS["Fast-Track"]:
        return "Fast-Track"
    elif score >= TIER_THRESHOLDS["Standard"]:
        return "Standard"
    elif score >= TIER_THRESHOLDS["Review"]:
        return "Review"
    else:
        return "Reject"

def generate_reason(row):
    score = row.get("score", 0)
    tier = row.get("tier", "")
    
    if tier == "Fast-Track":
        return "Strong candidate with excellent skills and detailed responses"
    elif tier == "Standard":
        return "Solid candidate with good potential"
    elif tier == "Review":
        return "Requires further evaluation"
    else:
        return "Does not meet minimum requirements"