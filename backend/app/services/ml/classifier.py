"""Loads the trained ticket classifier (ml/train.py -> backend/ml_models/classifier.joblib) once
and serves predictions. The SAME clean_text() used in training is applied here."""
import logging
from dataclasses import dataclass
from functools import lru_cache

import joblib

from app.core.config import get_settings
from app.services.ml.preprocess import clean_text

logger = logging.getLogger(__name__)


@dataclass
class Prediction:
    category: str
    probability: float
    top3: list[tuple[str, float]]


@lru_cache
def get_classifier():
    path = get_settings().classifier_path
    if not path.exists():
        raise FileNotFoundError(f"Classifier not found at {path}. Run `python ml/train.py` first.")
    model = joblib.load(path)
    logger.info("Ticket classifier loaded from %s", path.name)
    return model


def predict(text: str) -> Prediction:
    model = get_classifier()
    probs = model.predict_proba([clean_text(text)])[0]
    ranked = sorted(zip(model.classes_, probs), key=lambda x: x[1], reverse=True)
    return Prediction(
        category=str(ranked[0][0]),
        probability=float(ranked[0][1]),
        top3=[(str(c), round(float(p), 3)) for c, p in ranked[:3]],
    )
