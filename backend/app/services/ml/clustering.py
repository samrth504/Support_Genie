"""K-means clustering of ticket embeddings -> "trending issues".

1. Each ticket's (PII-masked) text is already embeddable with the RAG embedding model.
2. We try every K in a BUSINESS-DEFINED range (4..8 issue groups) and keep the K with the best
   *silhouette score* (how well-separated the clusters are: +1 = perfect, 0 = overlapping).
   Why a range and not 2..N? Support tickets all use similar "customer support" language, so
   silhouette scores are weak at every K (measured on the demo data: 0.23 at K=2, 0.18 at K=7,
   0.25 at K=10) and an unconstrained search always picks K=2 ("password" vs "everything else"),
   which is useless for a dashboard. A support team wants roughly 4-8 issue groups, so we search
   only there. Each cluster also needs ~3 tickets on average (K <= n // 3).
3. Each cluster is described by its top TF-IDF keywords (no LLM needed).
"""
from dataclasses import dataclass

import numpy as np
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import silhouette_score

from app.services.ml.preprocess import clean_text

MIN_TICKETS = 6
K_MIN, K_MAX = 4, 8          # how many "trending issue" groups a support dashboard should show
MIN_PER_CLUSTER = 3
RANDOM_STATE = 42
_EXTRA_STOP = {"num", "hi", "hello", "please", "help", "need", "want", "know", "shopnest", "thanks", "thank"}


@dataclass
class ClusterResult:
    labels: list[int]
    k: int
    silhouette: float
    keywords: dict[int, list[str]]


def _keywords(texts: list[str], labels: np.ndarray, k: int, top_n: int = 5) -> dict[int, list[str]]:
    vec = TfidfVectorizer(stop_words="english", ngram_range=(1, 2), max_features=3000, min_df=1)
    tfidf = vec.fit_transform([clean_text(t) for t in texts])
    terms = vec.get_feature_names_out()
    result: dict[int, list[str]] = {}
    for c in range(k):
        rows = np.where(labels == c)[0]
        mean = np.asarray(tfidf[rows].mean(axis=0)).ravel()
        picked: list[str] = []
        for idx in mean.argsort()[::-1]:
            if mean[idx] <= 0:      # term never appears in this cluster -> stop (else other clusters' words leak in)
                break
            term = terms[idx]
            if any(w in _EXTRA_STOP for w in term.split()):
                continue
            if any(term in p or p in term for p in picked):   # avoid "refund" + "refund status"
                continue
            picked.append(term)
            if len(picked) == top_n:
                break
        result[c] = picked
    return result


def cluster_tickets(texts: list[str], vectors: list[list[float]]) -> ClusterResult | None:
    """Returns None when there are too few tickets to cluster meaningfully."""
    n = len(texts)
    if n < MIN_TICKETS:
        return None
    X = np.asarray(vectors, dtype=np.float32)
    X = X / np.clip(np.linalg.norm(X, axis=1, keepdims=True), 1e-9, None)   # cosine geometry

    k_hi = max(2, min(K_MAX, n // MIN_PER_CLUSTER))
    k_lo = min(K_MIN, k_hi)
    best: tuple[KMeans, float, int] | None = None
    for k in range(k_lo, k_hi + 1):
        km = KMeans(n_clusters=k, n_init=10, random_state=RANDOM_STATE).fit(X)
        if len(set(km.labels_)) < 2:
            continue
        score = float(silhouette_score(X, km.labels_, metric="cosine"))
        if best is None or score > best[1]:
            best = (km, score, k)
    if best is None:
        return None

    km, score, k = best
    return ClusterResult(labels=km.labels_.tolist(), k=k, silhouette=round(score, 3),
                         keywords=_keywords(texts, km.labels_, k))
