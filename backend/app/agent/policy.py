"""ALL routing rules and thresholds in one place (tune them here, nowhere else).

confidence = 0.5 * LLM self-confidence
           + 0.3 * retrieval strength   (top similarity score mapped to 0..1)
           + 0.2 * classifier probability

Why three signals? We measured that retrieval score alone is not reliable: in the RAG demo
the "gift card" question (not in the docs) scored 0.62 while a valid Hinglish question scored
0.67 - only 0.05 apart. The LLM, which actually reads the chunks, adds a much clearer signal
(`answer_found`, `self_confidence`).
"""
import re

# --- confidence formula ---------------------------------------------------
W_LLM, W_RETRIEVAL, W_CLASSIFIER = 0.5, 0.3, 0.2
RETRIEVAL_FLOOR, RETRIEVAL_CEIL = 0.55, 0.85     # cosine similarity -> mapped to 0..1

# --- auto-reply gates -----------------------------------------------------
MIN_CONFIDENCE = 0.70                 # below this -> human review
HIGH_RISK_CATEGORIES = {"PAYMENT", "REFUND"}
MIN_CONFIDENCE_HIGH_RISK = 0.80       # money-related tickets need more certainty

# --- knowledge gaps -------------------------------------------------------
KNOWLEDGE_GAP_SCORE = 0.64            # top retrieval score below this = docs probably missing

# --- priority -------------------------------------------------------------
LOW_PRIORITY_CATEGORIES = {"SUBSCRIPTION", "FEEDBACK"}
URGENT_WORDS = (
    "urgent", "asap", "immediately", "fraud", "scam", "charged twice", "double charged",
    "money deducted", "turant", "jaldi", "abhi ke abhi",
)

REJECT_MESSAGE = (
    "We're sorry, but we couldn't process this request. If you need help with an order, "
    "account or payment, please raise a new ticket with the details."
)


# Money words: if the customer talks about money, treat the ticket as high-risk even when the
# classifier picked another category (found in testing: "charged my card twice" -> DELIVERY, p=0.22).
MONEY_WORDS = (
    "refunds?", "charged?", "charges", "deducted", "debited", "debit", "payments?", "paid", "money",
    "upi", "card", "wallet", "cashback", "paise", "paisa", "rupees?", "rs",
)
# Whole words only (so "stupid" does not match "upi"), plus the rupee sign anywhere
_MONEY_RE = re.compile(r"\b(?:" + "|".join(MONEY_WORDS) + r")\b|₹|\[card\]", re.IGNORECASE)


def is_high_risk(category: str | None, text: str) -> bool:
    return category in HIGH_RISK_CATEGORIES or bool(_MONEY_RE.search(text))


# A MONEY PROBLEM (not just a question about money) always goes to a human, however confident
# the AI is. Found in testing: "Charged twice" (PAYMENT, confidence 0.83) was auto-answered with
# the policy text "duplicate charges reverse in 5-7 days" - correct, but a real support team must
# look at the customer's actual transaction. Questions like "which payment methods do you accept"
# or "how many days does a UPI refund take" are still answered by the AI.
_MONEY_PROBLEM_RE = re.compile(
    r"charged (?:me )?(?:twice|double|two times|2 times)|double (?:charged?|payment|deduction)|"
    r"(?:took|taken|deducted|debited|cut) (?:money |payment |amount )?(?:twice|two times)|"
    r"(?:money|amount|payment|paise|paisa|rs|rupees)\b.{0,25}\b(?:deducted|debited|gone|taken|kat gaye|kat gaya|katt? gaye)|"
    r"\b(?:deducted|debited)\b|kat gaye|kat gaya|"
    r"refund\b.{0,30}\b(?:not|never|nahi|nhi)\b.{0,15}(?:received|credited|showing|shown|reflect(?:ed|ing)?|visible|aaya|mila|come|came|arrived)|"
    r"(?:not|never|nahi|nhi) (?:received|got|mila)\b.{0,15}\brefund|"
    r"\bfraud\b|\bscam\b|unauthori[sz]ed (?:transaction|payment|charge)",
    re.IGNORECASE,
)


def is_money_problem(text: str) -> bool:
    return bool(_MONEY_PROBLEM_RE.search(text))


def retrieval_strength(top_score: float) -> float:
    x = (top_score - RETRIEVAL_FLOOR) / (RETRIEVAL_CEIL - RETRIEVAL_FLOOR)
    return max(0.0, min(1.0, x))


def compute_confidence(llm_conf: float, top_score: float, classifier_prob: float) -> float:
    score = W_LLM * llm_conf + W_RETRIEVAL * retrieval_strength(top_score) + W_CLASSIFIER * classifier_prob
    return round(max(0.0, min(1.0, score)), 3)


def compute_priority(category: str | None, sentiment: str | None, text: str, injection: bool) -> str:
    lowered = text.lower()
    if injection or sentiment == "frustrated" or is_high_risk(category, text) or any(w in lowered for w in URGENT_WORDS):
        return "high"
    if category in LOW_PRIORITY_CATEGORIES and sentiment != "negative":
        return "low"
    return "medium"
