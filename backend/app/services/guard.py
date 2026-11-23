"""Safety layer that runs BEFORE any text reaches the LLM.

1. PII masking  - card numbers, phone numbers, emails, UPI IDs and Aadhaar-like numbers are
                  replaced with tags like [CARD]. The LLM provider never sees the real data.
2. Prompt-injection detection - simple, explainable heuristics. A flagged ticket skips the LLM
                  completely and goes to a human. (Defence in depth: the prompt also tells the
                  model to treat ticket text as data, not instructions.)
"""
import re
from dataclasses import dataclass, field

# Order of the rules matters: longer / more specific patterns first.
_PII_RULES: list[tuple[str, re.Pattern]] = [
    # 13-19 digits, optionally separated by spaces or dashes (credit / debit cards)
    ("CARD", re.compile(r"\b(?:\d[ -]?){12,18}\d\b")),
    # Aadhaar-style 12 digits in groups of 4
    ("ID_NUMBER", re.compile(r"\b\d{4}[ -]\d{4}[ -]\d{4}\b")),
    ("EMAIL", re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")),
    # UPI IDs look like name@bank (no dot after @)
    ("UPI_ID", re.compile(r"\b[\w.-]{2,}@[a-zA-Z]{2,}\b")),
    # Indian mobile numbers: optional +91 / 0, then 10 digits starting 6-9
    ("PHONE", re.compile(r"(?<!\d)(?:\+91[ -]?|0)?[6-9]\d{4}[ -]?\d{5}(?!\d)")),
    # CVV / OTP / PIN / password VALUES ("otp 482913", "password is Rahul@123").
    # The value must contain a digit, so "password bhool gaya" is NOT masked.
    ("SECRET", re.compile(r"\b(?:cvv|otp|pin|password|pwd)\b\s*(?:is|:|=|hai)?\s*(?=\S*\d)\S{3,}", re.IGNORECASE)),
]

_INJECTION_PATTERNS = [
    r"ignore (?:all |any |the )?(?:previous|prior|above|earlier|your) (?:instructions|rules|prompts?)",
    r"disregard (?:all |the )?(?:previous|above|your) (?:instructions|rules)",
    r"forget (?:all |your )?(?:previous )?(?:instructions|rules)",
    r"(?:reveal|show|print|repeat) (?:me )?(?:your|the) (?:system )?(?:prompt|instructions)",
    r"\bsystem prompt\b",
    r"\byou are now\b",
    r"\bact as (?:an? )?(?:admin|administrator|developer|dan)\b",
    r"\bdeveloper mode\b",
    r"\bjailbreak\b",
    r"\bnew instructions?:",
    r"instructions? (?:ignore|bhool) (?:karo|kar do|jao)",
    r"(?:approve|issue|give) (?:a )?(?:full )?refunds? (?:to )?(?:everyone|all users|without)",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


@dataclass
class GuardResult:
    masked_text: str
    pii_found: list[str] = field(default_factory=list)
    injection_flag: bool = False
    injection_match: str | None = None


def mask_pii(text: str) -> tuple[str, list[str]]:
    found: list[str] = []
    for tag, pattern in _PII_RULES:
        text, n = pattern.subn(f"[{tag}]", text)
        if n:
            found.append(tag)
    return text, found


def detect_injection(text: str) -> str | None:
    match = _INJECTION_RE.search(text)
    return match.group(0) if match else None


def run_guard(text: str) -> GuardResult:
    masked, pii = mask_pii(text)
    match = detect_injection(text)
    return GuardResult(masked_text=masked, pii_found=pii, injection_flag=match is not None, injection_match=match)
