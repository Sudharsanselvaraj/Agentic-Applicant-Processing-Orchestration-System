import re
from src.config import (
    SKILL_MATCH_SCORE,
    GITHUB_VALID_SCORE,
    DETAILED_ANSWER_SCORE,
    AI_PENALTY,
    FAST_RESPONSE_PENALTY,
    MISSING_DATA_PENALTY
)
from src.ai_detector import detect_ai_response

def score_candidate(row, required_skills=None):
    if required_skills is None:
        required_skills = ["python", "sql", "javascript", "java", "ml", "ai", "data"]
    
    score = 0
    reasons = []
    
    skills = row.get("skills", "")
    if skills:
        skill_list = [s.strip().lower() for s in skills.split(",")]
        matched = sum(1 for s in skill_list if any(r in s for r in required_skills))
        if matched > 0:
            score += min(matched * 10, SKILL_MATCH_SCORE)
            reasons.append(f"Matched {matched} relevant skills")
    else:
        score -= MISSING_DATA_PENALTY
        reasons.append("Missing skills")
    
    github = row.get("github", "")
    if github and github != "":
        if re.match(r"https?://github\.com/[\w-]+", github):
            score += GITHUB_VALID_SCORE
            reasons.append("Valid GitHub profile")
        else:
            score -= MISSING_DATA_PENALTY
            reasons.append("Invalid GitHub link")
    else:
        score -= MISSING_DATA_PENALTY
        reasons.append("No GitHub provided")
    
    answer = row.get("answer", "")
    if answer:
        word_count = len(answer.split())
        if word_count >= 30:
            score += DETAILED_ANSWER_SCORE
            reasons.append("Detailed answer provided")
        elif word_count >= 15:
            score += 15
            reasons.append("Moderate answer length")
        else:
            score += 5
            reasons.append("Short answer")
        
        ai_score = detect_ai_response(answer)
        if ai_score > 0.5:
            ai_penalty = int(AI_PENALTY * ai_score)
            score -= ai_penalty
            reasons.append(f"AI-generated content detected ({ai_score:.0%})")
    else:
        score -= MISSING_DATA_PENALTY
        reasons.append("No answer provided")
    
    response_time = row.get("response_time", 0)
    try:
        rt = float(response_time)
        if rt < 5:
            score -= FAST_RESPONSE_PENALTY
            reasons.append("Suspiciously fast response")
    except (ValueError, TypeError):
        pass
    
    return max(0, score), "; ".join(reasons)