"""
Semantic doctor matching using BGE-M3 (BAAI/bge-m3) embeddings + NumPy cosine similarity.
Embeddings are computed once at startup and cached in memory.
"""
import numpy as np
from sentence_transformers import SentenceTransformer
from data.doctors import DOCTORS, DOCTORS_BY_ID
import logging

logger = logging.getLogger(__name__)

_model: SentenceTransformer | None = None
_doctor_embeddings: dict[str, np.ndarray] = {}


def load_model():
    global _model, _doctor_embeddings
    logger.info("Loading BGE-M3 embedding model…")
    _model = SentenceTransformer("BAAI/bge-m3")
    # Pre-embed all specialty descriptions at startup
    for doc in DOCTORS:
        _doctor_embeddings[doc["id"]] = _model.encode(
            doc["specialty_description"], normalize_embeddings=True
        )
    logger.info("BGE-M3 loaded. %d doctor embeddings cached.", len(DOCTORS))


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    # Both are already L2-normalized when normalize_embeddings=True
    return float(np.dot(a, b))


def match_doctor(chief_complaint: str, threshold: float = 0.30) -> dict:
    """
    Returns matched doctor dict or {"matched": False, ...} if below threshold.
    """
    if _model is None:
        raise RuntimeError("Embedding model not loaded. Call load_model() at startup.")

    query_emb = _model.encode(chief_complaint, normalize_embeddings=True)

    scores = {
        doc_id: cosine_similarity(query_emb, doc_emb)
        for doc_id, doc_emb in _doctor_embeddings.items()
    }

    best_id = max(scores, key=scores.get)
    best_score = scores[best_id]

    logger.debug("Similarity scores: %s", scores)

    if best_score < threshold:
        return {
            "matched": False,
            "message": (
                "I'm sorry, our practice doesn't currently have a specialist "
                "for that condition. I'd recommend contacting your primary care "
                "physician for a referral."
            ),
        }

    doctor = dict(DOCTORS_BY_ID[best_id])
    return {
        "matched": True,
        "doctor": doctor,
        "confidence": round(best_score, 3),
    }
