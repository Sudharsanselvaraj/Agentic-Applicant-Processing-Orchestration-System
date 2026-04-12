from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from src.scorer import score_candidate
from src.ranker import get_tier

app = FastAPI(title="GenoTek Hiring Agent API")

class CandidateRequest(BaseModel):
    name: str
    skills: str
    github: str = ""
    answer: str = ""
    response_time: float = 0

@app.post("/score")
def score_candidate_api(candidate: CandidateRequest):
    row = {
        "name": candidate.name,
        "skills": candidate.skills,
        "github": candidate.github,
        "answer": candidate.answer,
        "response_time": candidate.response_time
    }
    
    score, reason, details = score_candidate(row)
    tier = get_tier(score)
    
    return {
        "name": candidate.name,
        "score": score,
        "tier": tier,
        "reason": reason
    }

@app.get("/health")
def health():
    return {"status": "ok"}