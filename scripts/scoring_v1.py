"""T-004 scoring rules, fixed in PREREG.md before any test image was generated. Used by ocr_run.py (controls), score.py and make_episode.py.

Primary gate = L1: the OCR text is NFKC-normalised, reduced to letters and digits (spaces, line breaks, punctuation such as the middle dot or
hyphen are ignored because OCR output for them is unreliable), casefolded; each expected label string, normalised the same way, must occur
at least `min_count` times, as a whole run (the character before the match must not equal the string's first character and the character
after it must not equal its last character, so GRAWWWWW does not pass for GRAWWWW).
L2 (strict) = the same without casefolding (a lowercase wordmark rendered in capitals fails).
An image passes a brief only if ALL its label strings pass ("image-level"); string-level rates are reported too."""
import re
import unicodedata


def strip_tags(t):
    t = re.sub(r"<\|ref\|>.*?<\|/ref\|>", "\n", t, flags=re.S)
    t = re.sub(r"<\|det\|>.*?<\|/det\|>", "\n", t, flags=re.S)
    t = re.sub(r"<[｜|][^>]*?[｜|]>", "\n", t)
    return t


def norm(s, fold=True):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c for c in s if c.isalnum())
    return s.casefold() if fold else s


def count_runs(text_norm, target_norm):
    if not target_norm:
        return 0
    n, i = 0, 0
    while True:
        j = text_norm.find(target_norm, i)
        if j < 0:
            return n
        prev = text_norm[j - 1] if j > 0 else ""
        nxt = text_norm[j + len(target_norm)] if j + len(target_norm) < len(text_norm) else ""
        if prev != target_norm[0] and nxt != target_norm[-1]:
            n += 1
        i = j + len(target_norm)


def check(text, expected, fold=True):
    """expected: [{"s": str, "min_count": int}] -> ([bool per string], all_ok)"""
    t = norm(strip_tags(text), fold)
    res = [count_runs(t, norm(e["s"], fold)) >= e.get("min_count", 1) for e in expected]
    return res, all(res)
