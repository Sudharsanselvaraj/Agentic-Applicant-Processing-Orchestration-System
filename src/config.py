import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

INPUT_FILE = DATA_DIR / "applicants.csv"
OUTPUT_FILE = OUTPUT_DIR / "ranked_candidates.csv"
DB_PATH = LOGS_DIR / "interactions.db"

SKILL_MATCH_SCORE = 30
GITHUB_VALID_SCORE = 20
DETAILED_ANSWER_SCORE = 30
AI_PENALTY = 20
FAST_RESPONSE_PENALTY = 10
MISSING_DATA_PENALTY = 15

AI_PHRASES = [
    "I'd be happy to help",
    "comprehensive overview",
    "in today's rapidly evolving",
    "as an AI language model",
    "here is a detailed explanation",
    "happy to help",
    "I'd be glad to",
    "Certainly!",
    "Here's a",
    "Below is"
]

TIER_THRESHOLDS = {
    "Fast-Track": 75,
    "Standard": 60,
    "Review": 40
}