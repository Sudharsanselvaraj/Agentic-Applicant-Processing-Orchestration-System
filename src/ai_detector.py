import re
import os
import numpy as np
from typing import Optional, Dict
from src.config import AI_PHRASES

_model = None

def _get_embedding_model():
    """Lazy-load sentence transformer model."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            print("⚠ sentence-transformers not installed - falling back to phrase-only detection")
            return None
    return _model

def _cosine_similarity(a, b):
    """Compute cosine similarity between two vectors."""
    a, b = np.array(a), np.array(b)
    norm_a, norm_b = np.linalg.norm(a), np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def _phrase_check(text: str) -> float:
    """Legacy phrase matching as fallback/secondary signal."""
    if not text:
        return 0.0
    
    text_lower = text.lower()
    phrase_matches = sum(1 for p in AI_PHRASES if p.lower() in text_lower)
    phrase_score = min(phrase_matches * 0.25, 0.75)
    
    patterns = [
        r"^here (is|are)", r"^certainly", r"^sure",
        r"as an (ai|language model)", r"i'd (be|glad|happy)",
        r"comprehensive", r"detailed explanation", r"step-by-step"
    ]
    pattern_matches = sum(1 for p in patterns if re.search(p, text_lower))
    pattern_score = min(pattern_matches * 0.15, 0.45)
    
    if len(text.split()) > 100 and phrase_matches >= 2:
        pattern_score += 0.15
    
    return min(phrase_score + pattern_score, 1.0)

def _call_groq_api(question: str, api_key: str) -> Optional[str]:
    """Call Groq API to get reference answer (FREE)."""
    try:
        import requests
        url = "https://api.groq.com/openai/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": "llama-3.1-8b-instant",
            "messages": [{"role": "user", "content": question}],
            "max_tokens": 500,
            "temperature": 0.7
        }
        response = requests.post(url, headers=headers, json=data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            return result['choices'][0]['message']['content']
        return None
    except Exception as e:
        print(f"⚠ Groq API error: {e}")
        return None

def _call_llm_api(question: str):
    """Call LLM API - tries Groq first, falls back to Anthropic. Returns (text, provider)."""
    # Try Groq first (free)
    groq_key = os.environ.get("GROQ_API_KEY", "")
    if groq_key:
        result = _call_groq_api(question, groq_key)
        if result:
            return result, "groq"
    
    # Fall back to Anthropic
    anthropic_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if anthropic_key:
        try:
            import anthropic
            client = anthropic.Anthropic(api_key=anthropic_key)
            response = client.messages.create(
                model="claude-3-haiku-20240307",
                max_tokens=500,
                messages=[{"role": "user", "content": question}]
            )
            for block in response.content:
                if hasattr(block, 'text'):
                    return block.text, "anthropic"
        except Exception as e:
            print(f"⚠ Anthropic API error: {e}")
    
    return None, None

def detect_ai_response(text: str, question: str = "", use_embeddings: bool = True) -> float:
    """
    Detect AI-generated responses.
    
    Without API: uses phrase matching
    With Groq/Anthropic: uses embedding similarity
    """
    if not text:
        return 1.0
    
    phrase_score = _phrase_check(text)
    
    # Check if embedding-based detection is enabled
    use_llm = os.environ.get("USE_EMBEDDINGS", "false").lower() == "true"
    if not use_llm or not question:
        return phrase_score
    
    model = _get_embedding_model()
    if model is None:
        return phrase_score
    
    # Get LLM reference answer
    llm_answer, provider = _call_llm_api(question)
    if not llm_answer:
        return phrase_score
    
    try:
        emb_candidate = model.encode([text])[0]
        emb_llm = model.encode([llm_answer])[0]
        similarity = _cosine_similarity(emb_candidate, emb_llm)
        
        final_score = max(similarity, phrase_score)
        return round(min(final_score, 1.0), 3)
    except Exception as e:
        print(f"⚠ Embedding error: {e}")
        return phrase_score

def detect_ai_response_detailed(text: str, question: str = "") -> Dict:
    """Detailed AI detection for debugging/demos."""
    result = {
        "score": 0.0,
        "embedding_similarity": 0.0,
        "phrase_match_score": 0.0,
        "provider": None,
        "flagged": False
    }
    
    if not text:
        result["flagged"] = True
        return result
    
    phrase_score = _phrase_check(text)
    result["phrase_match_score"] = phrase_score
    
    use_llm = os.environ.get("USE_EMBEDDINGS", "false").lower() == "true"
    if not use_llm or not question:
        result["score"] = phrase_score
        result["flagged"] = phrase_score > 0.5
        return result
    
    llm_answer, provider = _call_llm_api(question)
    if llm_answer:
        result["llm_reference"] = llm_answer[:200]
        result["provider"] = provider
        
        model = _get_embedding_model()
        if model:
            try:
                emb_candidate = model.encode([text])[0]
                emb_llm = model.encode([llm_answer])[0]
                similarity = _cosine_similarity(emb_candidate, emb_llm)
                
                result["embedding_similarity"] = similarity
                result["score"] = max(similarity, phrase_score)
                result["flagged"] = result["score"] > 0.75
            except Exception as e:
                result["score"] = phrase_score
                result["flagged"] = phrase_score > 0.5
    else:
        result["score"] = phrase_score
        result["flagged"] = phrase_score > 0.5
    
    return result