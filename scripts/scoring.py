"""T-004 scoring rules (PREREG.md; line-aware boundary fix 2026-10-20 16:45 UTC, before any test image existed; cross-line completion bug fixed 2026-10-22,
PREREG.md Addendum 3, report SCORER-FIX.md).

History:
 - 2026-10-20 first version joined the lines of the OCR text and so rejected LARA followed by "AI-GENERATED PRESENTER" (the next character, A, equals the last
   letter of LARA). Copy: scoring.py.bak-2026-10-20-prereg.
 - 2026-10-20 16:45 line-aware version (copy: scoring.py.pre-scorer-fix): lines kept apart by a separator that the match could optionally cross at ANY position.
   Bug: a letter from the start of the NEXT line could complete the target ("grawww" + next line "washed ..." counted as "grawwww"). Found 2026-10-22 by the verifier.
 - 2026-10-22 this version: the cross-line completion is restricted as described below. Same metric otherwise.

Primary rule L1: each OCR line is NFKC-normalised and reduced to letters and digits (spaces and punctuation such as the middle dot or the hyphen are
ignored because OCR output for them is unreliable), casefolded. An expected label string, normalised the same way, passes when it occurs at least `min_count`
times as a whole run. A run is either
  (a) inside ONE line: the character before the match must not equal its first character and the character after it must not equal its last one
      (so "GRAWWWWW" does not pass for GRAWWWW), or
  (b) across line breaks, only when the breaks split the target itself: the first part is the END of a line (the character before it must not equal the
      target's first character), every middle part is a WHOLE line, and the last part is the START of a later line that ends at a word boundary of that line
      (the continuation must not be the beginning of a longer word: "w" of "washed" cannot complete "grawww"; the character after the continuation must
      not equal the target's last character). Stacked "GRA" / "WWWW" = GRAWWWW and "AI-GENERATED" / "PRESENTER" pass.
Word boundaries are those of the raw line: runs of letters and digits separated by anything else (so "AI-GENERATED" has two words).
L2 strict = the same without casefolding (a lowercase wordmark drawn in capitals fails).
An image passes a brief only if ALL its label strings pass (image-level); string-level rates are reported too.

Known property, kept on purpose because it is part of the L1 definition (spaces ignored): inside one line a match may span a space, so "grawww washed" on ONE line
would still read as grawwww. `count_runs(..., word_aligned=True)` is the stricter sensitivity variant (every match must start and end on a word boundary of
its line); SCORER-FIX.md reports it next to the rule of record."""
import re
import unicodedata
from collections import namedtuple

# norm: letters and digits only (casefolded when fold); starts: indexes in `norm` where a raw word starts; ends: indexes where a raw word ends (len(norm) always included)
Line = namedtuple("Line", "norm starts ends")


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


def line_info(raw, fold=True):
    """raw line -> Line(norm, starts, ends); words are runs of letters and digits of the NFKC-normalised raw line."""
    s = unicodedata.normalize("NFKC", raw)
    toks, cur = [], []
    for c in s:
        if c.isalnum():
            cur.append(c)
        elif cur:
            toks.append("".join(cur))
            cur = []
    if cur:
        toks.append("".join(cur))
    parts = [t.casefold() if fold else t for t in toks]
    starts, ends, pos = set(), set(), 0
    for p in parts:
        starts.add(pos)
        pos += len(p)
        ends.add(pos)
    return Line("".join(parts), frozenset(starts), frozenset(ends))


def text_lines(text, fold=True):
    """OCR text -> list of Line (empty lines and lines with no letter or digit dropped)."""
    return [x for x in (line_info(l, fold) for l in strip_tags(text).splitlines()) if x.norm]


def find_runs(lines, t, word_aligned=False):
    """every admissible occurrence of the normalised target t, as ((line, start), (line, end)); see the module docstring for the rule."""
    n = len(t)
    out = []
    if not n:
        return out
    for i, L in enumerate(lines):
        s = L.norm
        # (a) inside one line
        j = s.find(t)
        while j >= 0:
            e = j + n
            ok = (j == 0 or s[j - 1] != t[0]) and (e == len(s) or s[e] != t[-1])
            if ok and word_aligned:
                ok = j in L.starts and e in L.ends
            if ok:
                out.append(((i, j), (i, e)))
            j = s.find(t, j + 1)
        # (b) across line breaks: a proper prefix of t is the END of line i
        for k in range(1, min(n - 1, len(s)) + 1):
            j = len(s) - k
            if s[j:] != t[:k]:
                continue
            if j > 0 and s[j - 1] == t[0]:
                continue
            if word_aligned and j not in L.starts:
                continue
            pos, m = k, i + 1
            while m < len(lines) and pos < n:
                M = lines[m]
                r = n - pos
                if len(M.norm) < r:
                    # middle part: the whole line
                    if M.norm != t[pos:pos + len(M.norm)]:
                        break
                    pos += len(M.norm)
                    m += 1
                    continue
                # last part: the START of line m, ending on a word boundary of that line
                if M.norm[:r] == t[pos:] and r in M.ends and (r == len(M.norm) or M.norm[r] != t[-1]):
                    out.append(((i, j), (m, r)))
                break
    return out


def count_runs(lines, target_norm, word_aligned=False):
    """number of non-overlapping admissible occurrences of target_norm in `lines` (list of Line from text_lines)."""
    found = sorted(find_runs(lines, target_norm, word_aligned))
    n, last_end = 0, None
    for start, end in found:
        if last_end is None or start >= last_end:
            n += 1
            last_end = end
    return n


def check(text, expected, fold=True, word_aligned=False):
    """expected: [{"s": str, "min_count": int}] -> ([bool per string], all_ok)"""
    lines = text_lines(text, fold)
    res = [count_runs(lines, norm(e["s"], fold), word_aligned) >= e.get("min_count", 1) for e in expected]
    return res, all(res)
