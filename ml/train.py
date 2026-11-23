"""Train the SupportGenie ticket-category classifier.

Run from the project root:
    .venv\\Scripts\\python.exe ml\\train.py

What it does (Hinglish summary):
  1. bitext_clean.csv padhta hai, numbers -> "num" karta hai (shared clean_text se)
  2. Stratified 80/20 train/test split
  3. 3 models compare karta hai (5-fold cross-validation, macro-F1):
       - Logistic Regression   (probabilities deta hai -> confidence score ke kaam aata hai)
       - Linear SVM            (aksar sabse accurate, lekin probability nahi deta)
       - Complement Naive Bayes (fast baseline, imbalance ke liye bana)
  4. Best model (jo probability de sake) ko poore train set pe fit karke test set pe evaluate karta hai
  5. Overfitting check: train score vs test score
  6. "Real-world" check: apne likhe messages (English + Hinglish) pe test
  7. Save: backend/ml_models/classifier.joblib + metrics JSON + confusion matrix PNG
"""
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import joblib
import matplotlib

matplotlib.use("Agg")  # graphs ko file mein save karo, window mat kholo
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
)
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.naive_bayes import ComplementNB
from sklearn.pipeline import Pipeline
from sklearn.svm import LinearSVC

# ---------------------------------------------------------------------------
# Paths + shared preprocessing (same function the backend uses at prediction time)
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
from app.services.ml.preprocess import clean_text  # noqa: E402

DATA_PATH = ROOT / "ml" / "data" / "bitext_clean.csv"
MODEL_DIR = ROOT / "backend" / "ml_models"
REPORT_DIR = ROOT / "ml" / "reports"
MODEL_PATH = MODEL_DIR / "classifier.joblib"
META_PATH = MODEL_DIR / "classifier_meta.json"

RANDOM_STATE = 42
TEST_SIZE = 0.2

# Apne likhe "real-world" messages: typos, Hinglish, real numbers.
# Dataset synthetic hai, isliye ye honest check hai ki model asli customers pe kaisa chalega.
REAL_WORLD_CHECK = [
    ("I forgot my password and can't log in to my account", "ACCOUNT"),
    ("how do i delete my profile permanently", "ACCOUNT"),
    ("where is my order 4582913, it was supposed to come yesterday", "ORDER"),
    ("I want to change the size in the order I placed this morning", "ORDER"),
    ("money was deducted twice for my purchase, please refund", "REFUND"),
    ("how many days will the refund take to reach my bank", "REFUND"),
    ("need the invoice INV-88231 for my office reimbursement", "INVOICE"),
    ("my UPI payment failed but amount got debited", "PAYMENT"),
    ("which payment methods do you accept", "PAYMENT"),
    ("how long does standard delivery take to Pune", "DELIVERY"),
    ("I need to update the shipping address for my parcel", "SHIPPING"),
    ("I want to talk to a human agent right now", "CONTACT"),
    ("your service is terrible, I want to file a complaint", "FEEDBACK"),
    ("unsubscribe me from your newsletter emails", "SUBSCRIPTION"),
    ("is there any penalty if I cancel early", "CANCEL"),
    # Hinglish
    ("mera order abhi tak nahi aaya, kab aayega?", "ORDER"),
    ("mujhe refund chahiye, paise wapas karo", "REFUND"),
    ("password bhool gaya hoon, account kaise kholun", "ACCOUNT"),
    ("payment fail ho gaya par paise kat gaye", "PAYMENT"),
    ("delivery address change karna hai", "SHIPPING"),
]


def build_candidates() -> dict[str, Pipeline]:
    """Har model = TF-IDF (text -> numbers) + classifier, ek Pipeline mein."""

    def tfidf() -> TfidfVectorizer:
        return TfidfVectorizer(
            ngram_range=(1, 2),  # single words + 2-word phrases ("cancel order")
            min_df=2,            # jo phrase sirf 1 baar aaye, use ignore karo (noise)
            sublinear_tf=True,   # bahut baar repeat hone wale word ko over-weight mat karo
        )

    return {
        "logistic_regression": Pipeline([
            ("tfidf", tfidf()),
            ("clf", LogisticRegression(max_iter=3000, class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
        "linear_svm": Pipeline([
            ("tfidf", tfidf()),
            ("clf", LinearSVC(class_weight="balanced", random_state=RANDOM_STATE)),
        ]),
        "complement_nb": Pipeline([
            ("tfidf", tfidf()),
            ("clf", ComplementNB()),
        ]),
    }


def load_data() -> pd.DataFrame:
    df = pd.read_csv(DATA_PATH)
    df["text"] = df["text"].astype(str).map(clean_text)  # numbers -> "num"
    before = len(df)
    df = df[df["text"].str.len() > 0].drop_duplicates(subset=["text", "category"])
    # number replace karne ke baad agar same text alag category mein aa gaya -> hatao
    n_labels = df.groupby("text")["category"].nunique()
    df = df[~df["text"].isin(n_labels[n_labels > 1].index)].reset_index(drop=True)
    print(f"Data: {before} -> {len(df)} rows after re-cleaning (numbers -> 'num')")
    return df


def save_confusion_matrix(y_true, y_pred, labels, path: Path) -> None:
    cm = confusion_matrix(y_true, y_pred, labels=labels, normalize="true")
    plt.figure(figsize=(9, 7))
    sns.heatmap(cm, annot=True, fmt=".2f", cmap="Blues", xticklabels=labels, yticklabels=labels, cbar=False)
    plt.xlabel("Predicted")
    plt.ylabel("Actual")
    plt.title("Confusion matrix (row-normalised, test set)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()


def main() -> None:
    t0 = time.time()
    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    df = load_data()
    X, y = df["text"], df["category"]

    # 1) Stratified split: har category ka ratio train aur test mein same
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_STATE
    )
    print(f"Train: {len(X_train)} | Test: {len(X_test)}")

    # 2) Model comparison with 5-fold cross-validation (sirf train data pe)
    cv = StratifiedKFold(n_splits=5, shuffle=True, random_state=RANDOM_STATE)
    candidates = build_candidates()
    cv_results = {}
    print("\n=== 5-fold cross-validation (macro F1) ===")
    for name, pipe in candidates.items():
        scores = cross_val_score(pipe, X_train, y_train, cv=cv, scoring="f1_macro", n_jobs=-1)
        cv_results[name] = {"mean": float(scores.mean()), "std": float(scores.std())}
        print(f"{name:<20} {scores.mean():.4f} ± {scores.std():.4f}")

    # 3) Best model chuno - lekin sirf wo jo predict_proba deta hai.
    #    Probability hamare confidence score ka hissa hai (CLAUDE.md -> routing formula).
    proba_models = [n for n, p in candidates.items() if hasattr(p.named_steps["clf"], "predict_proba")]
    best_name = max(proba_models, key=lambda n: cv_results[n]["mean"])
    overall_best = max(cv_results, key=lambda n: cv_results[n]["mean"])
    print(f"\nOverall best CV: {overall_best} | Chosen (needs probabilities): {best_name}")
    if overall_best != best_name:
        gap = cv_results[overall_best]["mean"] - cv_results[best_name]["mean"]
        print(f"  -> {overall_best} is {gap:.4f} better but gives no probabilities; trade-off accepted.")

    # 4) Final fit + test evaluation
    model = candidates[best_name]
    model.fit(X_train, y_train)

    train_pred = model.predict(X_train)
    test_pred = model.predict(X_test)
    train_f1 = f1_score(y_train, train_pred, average="macro")
    test_f1 = f1_score(y_test, test_pred, average="macro")
    test_acc = accuracy_score(y_test, test_pred)

    print("\n=== Test set ===")
    print(f"Accuracy : {test_acc:.4f}")
    print(f"Macro F1 : {test_f1:.4f}")
    print(f"Train F1 : {train_f1:.4f}  (gap {train_f1 - test_f1:+.4f} -> "
          f"{'OK, no strong overfitting' if train_f1 - test_f1 < 0.05 else 'possible overfitting'})")
    print("\n" + classification_report(y_test, test_pred, digits=3))

    labels = sorted(y.unique())
    save_confusion_matrix(y_test, test_pred, labels, REPORT_DIR / "confusion_matrix.png")

    # 5) Real-world check (English + Hinglish, real numbers, typos)
    rw_texts = [clean_text(t) for t, _ in REAL_WORLD_CHECK]
    rw_true = [c for _, c in REAL_WORLD_CHECK]
    rw_pred = model.predict(rw_texts)
    rw_conf = model.predict_proba(rw_texts).max(axis=1)
    rw_acc = float(np.mean(np.array(rw_pred) == np.array(rw_true)))
    print(f"=== Real-world check: {rw_acc:.0%} correct ({sum(np.array(rw_pred) == np.array(rw_true))}/{len(rw_true)}) ===")
    rw_rows = []
    for (raw, true), pred, conf in zip(REAL_WORLD_CHECK, rw_pred, rw_conf):
        mark = "OK " if pred == true else "XX "
        print(f"{mark}{conf:.2f}  {pred:<13} (expected {true:<13}) {raw}")
        rw_rows.append({"text": raw, "expected": true, "predicted": str(pred), "confidence": round(float(conf), 3)})

    # 6) Save model + metadata
    joblib.dump(model, MODEL_PATH, compress=3)
    metrics = {
        "model_name": best_name,
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "labels": labels,
        "cv_macro_f1": cv_results,
        "test_accuracy": round(float(test_acc), 4),
        "test_macro_f1": round(float(test_f1), 4),
        "train_macro_f1": round(float(train_f1), 4),
        "real_world_accuracy": round(rw_acc, 4),
        "real_world_examples": rw_rows,
        "per_class": classification_report(y_test, test_pred, output_dict=True),
    }
    META_PATH.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    (REPORT_DIR / "metrics.json").write_text(json.dumps(metrics, indent=2), encoding="utf-8")

    size_kb = MODEL_PATH.stat().st_size / 1024
    print(f"\nSaved model -> {MODEL_PATH} ({size_kb:.0f} KB)")
    print(f"Saved metrics -> {META_PATH} and {REPORT_DIR / 'metrics.json'}")
    print(f"Saved confusion matrix -> {REPORT_DIR / 'confusion_matrix.png'}")
    print(f"Done in {time.time() - t0:.1f}s")


if __name__ == "__main__":
    main()
