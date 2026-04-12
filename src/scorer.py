import re
import urllib.request
import urllib.error
import json
from typing import Dict, Optional
from src.config import (
    SKILL_MATCH_SCORE,
    GITHUB_VALID_SCORE,
    DETAILED_ANSWER_SCORE,
    AI_PENALTY,
    FAST_RESPONSE_PENALTY,
    MISSING_DATA_PENALTY
)
from src.ai_detector import detect_ai_response

# Cache GitHub API responses to avoid repeated calls
_github_cache: Dict[str, Dict] = {}

def check_github_profile(github_url: str) -> Dict:
    """
    Calls GitHub API to validate real profile quality.
    """
    global _github_cache
    
    # Handle invalid input
    if not github_url or github_url in ['', 'nan', 'None', 'NaN']:
        return {"score": -15, "reason": "No GitHub provided", "details": {}}
    
    # Validate URL format first
    match = re.search(r'github\.com/([\w-]+)', str(github_url))
    if not match:
        return {
            "score": -MISSING_DATA_PENALTY,
            "reason": "Invalid or missing GitHub URL",
            "details": {}
        }
    
    username = match.group(1)
    
    # Check cache
    if username in _github_cache:
        return _github_cache[username]
    
    # Call GitHub API
    try:
        url = f"https://api.github.com/users/{username}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "APOS-Candidate-Scorer",
                "Accept": "application/vnd.github.v3+json"
            }
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            user_data = json.loads(response.read().decode())
        
        public_repos = user_data.get("public_repos", 0)
        followers = user_data.get("followers", 0)
        following = user_data.get("following", 0)
        created_at = user_data.get("created_at", "")
        updated_at = user_data.get("updated_at", "")
        
        # Score based on activity
        if public_repos == 0:
            score = -15
            reason = f"GitHub has 0 public repos ({username})"
        elif public_repos < 3:
            score = 5
            reason = f"GitHub: {public_repos} repos, low activity"
        elif public_repos >= 10 or followers >= 5:
            score = 25
            reason = f"GitHub: {public_repos} repos, {followers} followers — active"
        else:
            score = 15
            reason = f"GitHub: {public_repos} repos — moderate activity"
        
        result = {
            "score": score,
            "reason": reason,
            "details": {
                "public_repos": public_repos,
                "followers": followers,
                "following": following,
                "account_age": created_at[:10] if created_at else "unknown",
                "last_updated": updated_at[:10] if updated_at else "unknown"
            }
        }
        
        _github_cache[username] = result
        return result
        
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return {
                "score": -15,
                "reason": f"GitHub user '{username}' not found",
                "details": {"error": "404"}
            }
        return {
            "score": 0,
            "reason": f"GitHub API error: {e.code}",
            "details": {"error": e.code}
        }
    except Exception as e:
        return {
            "score": 0,
            "reason": f"GitHub API unreachable: {str(e)[:50]}",
            "details": {"error": str(e)[:100]}
        }

def clear_github_cache():
    """Clear the GitHub API cache."""
    global _github_cache
    _github_cache = {}

def score_candidate(row, required_skills=None):
    if required_skills is None:
        required_skills = ["python", "sql", "javascript", "java", "ml", "ai", "data"]
    
    score = 0
    reasons = []
    details = {}
    
    # 1. Skills matching
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
    
    # 2. GitHub validation (REAL API call now!)
    github = str(row.get("github", "")) if row.get("github") else ""
    if github and github not in ['', 'nan', 'None']:
        gh_result = check_github_profile(github)
        score += gh_result["score"]
        reasons.append(gh_result["reason"])
        if gh_result.get("details"):
            details["github"] = gh_result["details"]
    else:
        score -= MISSING_DATA_PENALTY
        reasons.append("No GitHub provided")
    
    # 3. Answer quality + AI detection
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
        
        # Get the screening question for AI detection
        question = row.get("screening_question", "")
        ai_score = detect_ai_response(answer, question=question)
        if ai_score > 0.5:
            ai_penalty = int(AI_PENALTY * ai_score)
            score -= ai_penalty
            reasons.append(f"AI-generated content ({ai_score:.0%})")
            details["ai_detection"] = {"score": ai_score, "flagged": ai_score > 0.5}
    else:
        score -= MISSING_DATA_PENALTY
        reasons.append("No answer provided")
    
    # 4. Response timing
    response_time = row.get("response_time", 0)
    try:
        rt = float(response_time)
        if rt < 5:
            score -= FAST_RESPONSE_PENALTY
            reasons.append("Suspiciously fast response")
    except (ValueError, TypeError):
        pass
    
    return max(0, score), "; ".join(reasons), details