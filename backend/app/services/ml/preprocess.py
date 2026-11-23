"""Text preprocessing shared by training (ml/train.py) and the live backend.

Single source of truth: the model must see text cleaned EXACTLY the same way
during training and during prediction, otherwise accuracy silently drops.
"""
import re

# {{Order Number}}, {{Invoice Number}} ... placeholders from the Bitext dataset.
# Their names leak the category, so they are removed.
PLACEHOLDER_RE = re.compile(r"\{\{.*?\}\}")

# Any number (invoice ids, order ids, amounts). Specific numbers would be
# memorised by the model, so every number becomes the same token "num".
NUMBER_RE = re.compile(r"\d+")

WHITESPACE_RE = re.compile(r"\s+")


def clean_text(text: str) -> str:
    """lowercase -> remove placeholders -> numbers to 'num' -> collapse spaces.

    Typos are intentionally kept: real customers make typos too.
    """
    text = str(text).lower()
    text = PLACEHOLDER_RE.sub(" ", text)
    text = NUMBER_RE.sub(" num ", text)
    text = WHITESPACE_RE.sub(" ", text).strip()
    return text
