import re
from src.config import AI_PHRASES

def detect_ai_response(text):
    if not text:
        return 1.0
    
    text_lower = text.lower()
    phrase_matches = 0
    
    for phrase in AI_PHRASES:
        if phrase.lower() in text_lower:
            phrase_matches += 1
    
    phrase_score = min(phrase_matches * 0.3, 1.0)
    
    patterns = [
        r"^here (is|are)",
        r"^certainly",
        r"^sure",
        r"as an (ai|language model)",
        r"i'd (be|glad|happy)",
        r"comprehensive",
        r"detailed explanation",
        r"step-by-step",
        r"in today's rapidly"
    ]
    
    pattern_matches = sum(1 for p in patterns if re.search(p, text_lower))
    pattern_score = min(pattern_matches * 0.2, 0.6)
    
    if len(text.split()) > 100 and phrase_matches >= 2:
        pattern_score += 0.2
    
    total_score = min(phrase_score + pattern_score, 1.0)
    return round(total_score, 2)