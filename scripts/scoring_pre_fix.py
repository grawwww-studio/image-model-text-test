"""T-004 scoring rules (PREREG.md; line-aware boundary fix 2026-10-20 16:45 UTC, before any test image existed: the first version joined the lines of the
OCR text and so rejected LARA followed by "AI-GENERATED..." because the next character, A, equals the last letter of LARA).

Primary rule L1: each OCR line is NFKC-normalised and reduced to letters and digits (spaces and punctuation such as the middle dot or the hyphen are
ignored because OCR output for them is unreliable), casefolded. Lines are kept apart by a separator. An expected label string, normalised the same way,
passes when it occurs at least `min_count` times as a whole run: it may continue over a line break (stacked "GRA" / "WWWW" = GRAWWWW), but the
character before the match must not equal its first character and the character after it must not equal its last one (inside the same line), so
"GRAWWWWW" does not pass for GRAWWWW and a line break counts as a boundary.
L2 strict = the same without casefolding (a lowercase wordmark drawn in capitals fails).
An image passes a brief only if ALL its label strings pass (image-level); string-level rates are reported too."""
import re
import unicodedata

SEP = "\x00"


def strip_tags(t):
    t = re.sub(r"<\|ref\|>.*?<\|/ref\|>", "\n", t, flags=re.S)
    t = re.sub(r"<\|det\|>.*?<\|/det\|>", "\n", t, flags=re.S)
    t = re.sub(r"<[｜|][^>]*?[｜|]>", "\n", t)
    return t


def norm_line(s, fold=True):
    s = unicodedata.normalize("NFKC", s)
    s = "".join(c for c in s if c.isalnum())
    return s.casefold() if fold else s


def norm(s, fold=True):
    """whole string (no line structure) -> letters and digits only."""
    return norm_line(s, fold)


def text_lines(text, fold=True):
    return [x for x in (norm_line(l, fold) for l in strip_tags(text).splitlines()) if x]


def count_runs(lines, target_norm):
    """occurrences of target in the lines joined with SEP; the target may span a SEP; boundaries as described above."""
    if not target_norm:
        return 0
    hay = SEP.join(lines)
    pat = SEP + "?"
    rx = re.compile("(?<!" + re.escape(target_norm[0]) + ")" + pat.join(re.escape(c) for c in target_norm) + "(?!" + re.escape(target_norm[-1]) + ")")
    return len(rx.findall(hay))


def check(text, expected, fold=True):
    """expected: [{"s": str, "min_count": int}] -> ([bool per string], all_ok)"""
    lines = text_lines(text, fold)
    res = [count_runs(lines, norm(e["s"], fold)) >= e.get("min_count", 1) for e in expected]
    return res, all(res)
