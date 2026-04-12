# GenoTek AI Hiring Agent
# Auto-initialize databases on import

from dotenv import load_dotenv
load_dotenv()  # Load all env vars from .env

from src.config import DATA_DIR, OUTPUT_DIR, LOGS_DIR, CACHE_DIR
from src.anti_cheat import init_anti_cheat_db
from src.email_manager import init_email_db
from src.learner import init_learner_db

DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

init_anti_cheat_db()
init_email_db()
init_learner_db()

__all__ = [
    "scorer",
    "ranker", 
    "anti_cheat",
    "email_manager",
    "learner",
    "gmail_integration",
    "response_generator",
    "ai_detector"
]