#!/usr/bin/env python3
"""Unit tests for scripts/scoring.py (written 2026-10-22 with the cross-line fix, results/PREREG.md Addendum 3, results/SCORER-FIX.md).
Run from the repository folder:  python3 -m unittest -v scripts/test_scoring.py      (standard library only, CPU, no model)

Three groups:
  1. the b07 Qwen case (a letter of the NEXT line completing "grawww") must FAIL, with the stored OCR texts of the real images;
  2. the original LARA / AI-GENERATED PRESENTER case (why the line-aware version exists) must still pass;
  3. a target genuinely split across lines must pass, including the stored real ones (GRA / WWWW, VISIT / NORDHAVN, FRESH / BREAD / DAILY / 7AM-2PM).
The stored OCR texts come from results/results.json, results_extra.json and results_battery3.json (the reader of record's text for each image), plus one control text written
out below. The two earlier scorers (scoring_v1.py, the joined version; scoring_pre_fix.py, the line-aware version with the bug) are loaded only to prove the problems
existed on the same input."""
import json
import unittest
from importlib.machinery import SourceFileLoader
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
import sys  # noqa: E402

sys.path.insert(0, str(HERE))
import scoring  # noqa: E402

OLD_PATH = HERE / "scoring_pre_fix.py"
OLD = SourceFileLoader("scoring_pre_fix", str(OLD_PATH)).load_module() if OLD_PATH.exists() else None

B07 = [{"s": "grawwww", "min_count": 1}, {"s": "washed black hoodie", "min_count": 1}, {"s": "AI-generated · fictional model and brand", "min_count": 1}]
B10 = [{"s": "LARA", "min_count": 1}, {"s": "AI-GENERATED PRESENTER", "min_count": 1}]
H4 = [{"s": "FRESH BREAD DAILY 7AM-2PM", "min_count": 1}]


def one(text, target, fold=True, min_count=1, word_aligned=False):
    return scoring.check(text, [{"s": target, "min_count": min_count}], fold, word_aligned)[1]


# the one control text used below (reader of record, configuration c2, control image cal2_moss-official_11): the title is "VISIT", the next block "NORDHAVN"
CONTROL_TEXT = {"cal2_moss-official_11.png": "\u2014 VISIT \u2014\n\nNORDHAVN\n\n\n\n\n\n\n\nSUMMER 1962"}
_CACHE = {}


def _json(name):
    if name not in _CACHE:
        _CACHE[name] = json.loads((ROOT / "results" / name).read_text(encoding="utf-8"))
    return _CACHE[name]


def stored(ocr_file, key):
    """text of the reader of record (c2) for one image; ocr_file names the raw file it came from in our working folder, key the image."""
    if ocr_file == "controlsreal_unl_c2.json":
        return CONTROL_TEXT[key]
    if ocr_file == "test_unl_c2.json":
        rows = {e["file"]: e for e in _json("results.json")["per_image"]}
        return rows[key]["unl_c2_text"]
    if ocr_file.startswith("extra_") and ocr_file.endswith("_unl_c2.json"):
        arm = ocr_file[len("extra_"):-len("_unl_c2.json")]
        rows = {e["file"]: e for e in _json("results_extra.json")["per_image"]}
        return rows[f"{arm}/{key}"]["unl_c2_text"]
    if ocr_file.startswith("b3_h4_") and ocr_file.endswith("_unl_c2.json"):
        arm = ocr_file[len("b3_h4_"):-len("_unl_c2.json")]
        rows = {(e["prompt"], e["arm"], e["seed"]): e for e in _json("results_battery3.json")["per_image"]}
        pid, seed = key.split("_")[0], int(key[:-4].rsplit("_", 1)[1])
        return rows[(pid, arm, seed)]["ocr_c2_text"]
    raise unittest.SkipTest(f"no stored text for {ocr_file}")


class B07NextLineLetter(unittest.TestCase):
    """group 1: the b07 hoodie card. Three w on the first line, then the line 'washed black hoodie': the w of 'washed' is not a fourth w."""

    def test_inline_text_fails(self):
        t = "grawww\n\nwashed black hoodie\n\nAI-generated · fictional model and brand"
        self.assertFalse(one(t, "grawwww"))
        self.assertFalse(scoring.check(t, B07)[1])
        # the two other strings of the card are still read fine, only the wordmark fails
        self.assertEqual(scoring.check(t, B07)[0], [False, True, True])

    def test_strict_case_also_fails(self):
        self.assertFalse(one("grawww\nwashed black hoodie", "grawwww", fold=False))

    def test_stored_qwen21_102_103_c2(self):
        for key in ("b07-endcard-hoodie_qwen21_102.png", "b07-endcard-hoodie_qwen21_103.png"):
            txt = stored("extra_qwen21_unl_c2.json", key)
            self.assertFalse(scoring.check(txt, B07)[1], key)
            if OLD:
                self.assertTrue(OLD.check(txt, B07)[1], "the pre-fix scorer passed this image (the bug): " + key)

    def test_stored_qwen2512_101_c2(self):
        txt = stored("extra_qwena_unl_c2.json", "b07-endcard-hoodie_qwena_101.png")
        self.assertFalse(scoring.check(txt, B07)[1])
        if OLD:
            self.assertTrue(OLD.check(txt, B07)[1])

    def test_stored_krea_and_moss_three_w_reads_fail_too(self):
        for key in ("b07-endcard-hoodie_krea-dense_101.png", "b07-endcard-hoodie_moss-layout_101.png"):
            txt = stored("test_unl_c2.json", key)
            self.assertFalse(scoring.check(txt, B07)[1], key)

    def test_four_w_on_one_line_still_passes(self):
        # the OCR itself read four w: that pass is the OCR's, not ours
        txt = stored("test_unl_c2.json", "b07-endcard-hoodie_krea-dense_103.png")
        self.assertTrue(scoring.check(txt, B07)[1])
        self.assertTrue(one("grawwww\n\nwashed black hoodie", "grawwww"))

    def test_continuation_must_not_start_a_longer_word(self):
        self.assertFalse(one("GRAW\nWWWASHED", "GRAWWWW"))
        self.assertFalse(one("GRAWWW\nWASHED BLACK HOODIE", "GRAWWWW"))

    def test_lone_w_line_counts_as_a_continuation(self):
        # rule as written: the continuation is a whole word (here the whole line), so it is not 'the start of another word'
        self.assertTrue(one("GRAWWW\nW", "GRAWWWW"))


class LaraAiGeneratedPresenter(unittest.TestCase):
    """group 2: why the line-aware version exists. 'LARA' then 'AI-GENERATED PRESENTER': the A that starts the next line must not make the
    boundary check reject LARA, and the second string reads across its own words."""

    TEXT = "LARA\n\nAI-GENERATED PRESENTER"

    def test_both_strings_pass(self):
        self.assertEqual(scoring.check(self.TEXT, B10), ([True, True], True))

    def test_stored_krea_b10(self):
        txt = stored("test_unl_c2.json", "b10-ai-badge_krea-dense_101.png")
        self.assertTrue(scoring.check(txt, B10)[1])

    def test_pre_prereg_joined_version_would_reject(self):
        # documents the original problem with the first (joined) version: LARA + A... = LARAA, last-letter rule rejects
        if not (HERE / "scoring_v1.py").exists():
            self.skipTest("scoring_v1.py missing")
        m = SourceFileLoader("scoring_v1", str(HERE / "scoring_v1.py")).load_module()
        self.assertFalse(m.check(self.TEXT, B10)[0][0])

    def test_lara_not_completed_from_the_next_line(self):
        # LAR on one line and AI-GENERATED... on the next is not LARA (the A would come from the start of another word)
        self.assertFalse(one("LAR\nAI-GENERATED PRESENTER", "LARA"))

    def test_two_line_split_of_the_second_string(self):
        self.assertTrue(one("LARA\nAI-GENERATED\nPRESENTER", "AI-GENERATED PRESENTER"))


class GenuineSplit(unittest.TestCase):
    """group 3: the break splits the target itself and the continuation is a whole word (or whole line): pass."""

    def test_stacked_wordmark(self):
        self.assertTrue(one("GRA\nWWWW", "GRAWWWW"))
        self.assertTrue(one("GRA\n\nWWWW\n\nLIME", "GRAWWWW"))

    def test_stacked_wordmark_with_three_w_fails(self):
        self.assertFalse(one("GRA\nWWW", "GRAWWWW"))
        self.assertFalse(one("GRA\nWWW\n\nWASHED", "GRAWWWW"))

    def test_stacked_wordmark_five_w_fails(self):
        self.assertFalse(one("GRA\nWWWWW", "GRAWWWW"))
        self.assertFalse(one("GRAWWWWW", "GRAWWWW"))

    def test_continuation_may_be_followed_by_other_words_on_its_line(self):
        self.assertTrue(one("GRA\nWWWW LIME", "GRAWWWW"))
        self.assertFalse(one("GRA\nWWWW WIDE", "GRAWWWW"))  # an extra W after the break would be a fifth w

    def test_words_split_over_two_lines(self):
        self.assertTrue(one("AI-GENERATED\nPRESENTER", "AI-GENERATED PRESENTER"))
        self.assertTrue(one("AI-generated · fictional\nproduct and brand", "AI-generated · fictional product and brand"))

    def test_four_line_sign(self):
        self.assertTrue(scoring.check("FRESH\n\nBREAD\n\nDAILY\n\n7AM-2PM", H4)[1])
        self.assertTrue(scoring.check("FRESH BREAD\nDAILY 7AM-2PM.", H4)[1])
        self.assertTrue(scoring.check("FRESH\nBREAD\nDAILY\n7AM-2PM\nDINLAND\nDAILY\n7AM-2PM", H4)[1])

    def test_four_line_sign_with_a_wrong_middle_line_fails(self):
        self.assertFalse(scoring.check("FRESH\nBREAD\nDAILX\n7AM-2PM", H4)[1])
        self.assertFalse(scoring.check("FRESH\nDREAD\nDAILY\n7AM-2PM", H4)[1])

    def test_a_middle_part_must_be_a_whole_line(self):
        self.assertFalse(scoring.check("FRESH\nBREAD EXTRA\nDAILY\n7AM-2PM", H4)[1])

    def test_stored_real_splits(self):
        self.assertTrue(scoring.check(stored("test_unl_c2.json", "b05-neon-can500_krea-dense_103.png"), [{"s": "GRAWWWW"}])[1])
        self.assertTrue(scoring.check(stored("test_unl_c2.json", "b05-neon-can500_krea-ie_101.png"), [{"s": "GRAWWWW"}])[1])
        self.assertTrue(scoring.check(stored("controlsreal_unl_c2.json", "cal2_moss-official_11.png"), [{"s": "VISIT NORDHAVN"}])[1])
        self.assertTrue(scoring.check(stored("b3_h4_qwen21_unl_c2.json", "h4-chalkboard_qwen21_101.png"), H4)[1])

    def test_stored_split_with_one_w_short_fails(self):
        self.assertFalse(scoring.check(stored("test_unl_c2.json", "b08-duo-cans_moss-layout_101.png"), [{"s": "GRAWWWW", "min_count": 2}])[1])


class UnchangedDefinitions(unittest.TestCase):
    """L1/L2, boundaries inside a line and min_count are the definitions of PREREG.md and did not change."""

    def test_l1_casefold_and_punctuation(self):
        self.assertTrue(one("Grawwww", "grawwww"))
        self.assertTrue(one("LIME · BERRY", "LIME BERRY"))
        self.assertTrue(one("LIMEBERRY", "LIME · BERRY"))

    def test_l2_strict_is_case_sensitive(self):
        self.assertTrue(one("grawwww", "grawwww", fold=False))
        self.assertFalse(one("GRAWWWW", "grawwww", fold=False))
        self.assertTrue(one("GRAWWWW", "grawwww", fold=True))

    def test_boundary_inside_a_line(self):
        self.assertFalse(one("GRAWWWWW", "GRAWWWW"))
        self.assertFalse(one("GGRAWWWW", "GRAWWWW"))
        self.assertTrue(one("XGRAWWWW", "GRAWWWW"))  # no word-start rule in L1; the sensitivity variant below shows no stored image depends on it

    def test_min_count(self):
        self.assertFalse(one("GRAWWWW", "GRAWWWW", min_count=2))
        self.assertTrue(one("GRAWWWW\nGRAWWWW", "GRAWWWW", min_count=2))
        self.assertTrue(one("GRA\nWWWW\nGRA\nWWWW", "GRAWWWW", min_count=2))
        self.assertTrue(one("GRAWWWW\nGRA\nWWWW", "GRAWWWW", min_count=2))
        self.assertFalse(one("GRA\nWWWW", "GRAWWWW", min_count=2))

    def test_det_tags_and_empty_text(self):
        raw = "<|det|>title [1, 2, 3, 4]<|/det|>grawww\n<|det|>title [1, 2, 3, 4]<|/det|>washed black hoodie"
        self.assertFalse(one(raw, "grawwww"))
        self.assertFalse(one("", "grawwww"))
        self.assertFalse(one("\n\n", "grawwww"))

    def test_same_line_spans_a_space_by_definition_but_word_aligned_variant_rejects(self):
        # L1 ignores spaces, so ONE line 'grawww washed' still reads as grawwww. No stored OCR text has this (SCORER-FIX.md); the variant exists to prove it.
        self.assertTrue(one("grawww washed black hoodie", "grawwww"))
        self.assertFalse(one("grawww washed black hoodie", "grawwww", word_aligned=True))


class OldVersusNew(unittest.TestCase):
    def test_old_scorer_accepted_the_bug_input(self):
        if not OLD:
            self.skipTest("pre-fix scorer missing")
        t = "grawww\n\nwashed black hoodie\n\nAI-generated · fictional model and brand"
        self.assertTrue(OLD.check(t, B07)[1])
        self.assertFalse(scoring.check(t, B07)[1])

    def test_old_and_new_agree_on_the_lara_case(self):
        if not OLD:
            self.skipTest("pre-fix scorer missing")
        t = "LARA\n\nAI-GENERATED PRESENTER"
        self.assertEqual(OLD.check(t, B10), scoring.check(t, B10))


if __name__ == "__main__":
    unittest.main(verbosity=2)
