# Scorer fix: a letter from the next OCR line could complete a target string (2026-10-22)

Written on 2026-10-22 (CPU only, no model run), before the video and this repository were published. Rule-change record: `PREREG.md` Addendum 3 (in this folder). The comparison tables below were produced by a comparison script of ours that reads the stored JSON files (not included); `scripts/rescore.py` in this repository recomputes the new numbers from the stored reader texts. "Old" = scored with `scripts/scoring_pre_fix.py`; "new" = scored with the fixed `scripts/scoring.py`. "AI reading" = the agent visual reading (an AI model, not a person).

## 0. Short version

- **The bug.** `scoring.py` (the line-aware version of 2026-10-20) let a match cross a line break at any position of the target. On the b07 hoodie card a reader text `grawww` followed by the line `washed black hoodie` counted as `grawwww`: the w of "washed" was the fourth w. The pass was ours, not the reader's.
- **The fix.** A target matches inside one line, or across line breaks only when the breaks split the target itself and the continuation is not the start of a longer word. L1/L2, boundaries, `min_count`, readers, thresholds and the criterion are untouched. 31 unit tests (`scripts/test_scoring.py`): b07 Qwen fails, LARA / AI-GENERATED PRESENTER still passes, genuine splits pass.
- **What changed.** Re-scoring every stored OCR output (1 177 items: 975 label, 190 control, 12 battery-3 h4): only the target string `grawwww` of b07 changes. 36 image-level results across all readers go from pass to fail (12 of them for the reader of record c2), none from fail to pass. The controls score identically: c2 is still the chosen configuration and still valid (sensitivity 20/25 = 0.80, specificity 12/13 = 0.92).
- **The verdict of record changes, by the pre-registered rule applied mechanically.** Reader of record c2, best MOSS arm vs krea-dense: 8 of 10 briefs (unchanged), rerolls **MOSS 15 vs Krea 16 (was 14 vs 14)**: strictly fewer, so the criterion reads **MET (was NOT MET, by a tie)**. The margin is one reroll on three seeds per cell and the reader agrees with the AI reading on only 48 of 105 images. Each MOSS arm alone still FAILS. The AI reading, which already said "would pass" (9/10, 1 vs 3), is unchanged.

### 0.1 The numbers, old -> new

| item | old | new |
|---|---|---|
| Verdict of record (c2, best MOSS arm vs krea-dense) | 8/10 briefs, rerolls 14 vs 14: **FAIL** (tie) | 8/10 briefs, rerolls 15 vs 16: **PASS** (one reroll) |
| moss-prompt alone (c2) | 7/10, rr 19 vs 14: FAIL | 7/10, rr 20 vs 16: FAIL |
| moss-layout alone (c2) | 8/10, rr 15 vs 14: FAIL | 7/10, rr 18 vs 16: FAIL |
| c0 / c1 / union / RapidOCR / vision model / AI reading, headline | c0 10/10, 10 vs 18, PASS; c1 9/10, 16 vs 18, PASS; union 10/10, 7 vs 11, PASS; RapidOCR 9/10, 5 vs 14, PASS; vlm 9/10, 1 vs 4, PASS; AI 9/10, 1 vs 3, PASS | c0 10/10, 10 vs 19, PASS; c1 8/10, 17 vs 18, PASS; union 10/10, 7 vs 11, PASS; RapidOCR 9/10, 5 vs 14, PASS; vlm 9/10, 2 vs 4, PASS; AI 9/10, 1 vs 3, PASS. No reader's headline verdict flips except c2 |
| c2 agreement with the AI reading, four frozen arms | 49/105 | 48/105 |
| c2 agreement, extra arms Qwen-2.1 + FIBO + Qwen-2512 | 49/90 | 51/90 |
| c2 agreement, Klein | 11/30 | 10/30 |
| c2 agreement, all 225 | 109/225 | 109/225 |
| c2 images passing out of 30 | Krea 12, MOSS-prompt 9, MOSS-layout 11, Qwen-2.1 9, FIBO 13, Qwen-2512 6, Klein 11 (krea-ie 3 of 15) | Krea **10**, MOSS-prompt **7**, MOSS-layout **8**, Qwen-2.1 **7**, FIBO **12**, Qwen-2512 **5**, Klein **10** (krea-ie 3 of 15) |
| b07 seed 101, c2 (whole card) | Krea PASS, MOSS-prompt PASS, MOSS-layout PASS, Qwen-2.1 PASS, FIBO FAIL, Qwen-2512 PASS, Klein PASS | Krea **FAIL**, MOSS-prompt **FAIL**, MOSS-layout **FAIL**, Qwen-2.1 PASS, FIBO FAIL, Qwen-2512 **FAIL**, Klein **FAIL** |
| battery 3, h4 chalkboard, OCR c2 (12 images) | Krea F/F, MOSS F/F, Qwen-2.1 P/P, FIBO F/P, Qwen-2512 P/P, Klein P/P | identical, 0 of 12 changed |
| controls: c2 sensitivity / specificity / valid / configuration chosen | 0.80 / 0.923 / yes / c2 | identical (0 of 190 control OCR items changed) |

The full tables (every reader, per-arm rerolls and censored briefs, every changed image, the rule applied to the extra arms) are in section 5.

## 1. The bug

- Where: `scripts/scoring.py` (before the fix: `scripts/scoring_pre_fix.py`), `count_runs`. The line-aware version (Addendum 1, 2026-10-20 16:45 UTC) joined the OCR lines with a separator and built the pattern `g\0?r\0?a\0?w\0?w\0?w\0?w`: the separator was optional between ANY two characters of the target, so any letter at the start of the next line could finish the match. It replaced the first version (all lines joined, `scripts/scoring_v1.py`), which rejected LARA followed by "AI-GENERATED PRESENTER" because the next character, A, equals the last letter of LARA.
- Example from our data: Qwen-Image-2512, b07, seed 101, reader c2: `grawww` / `washed black hoodie` / `AI generated · fictional model and brand`. Old scorer: the string `grawwww` found 1 run (`grawww` + the w of `washed`). The image has three w; the reader said three w.
- Reach: scanning all 1 177 stored OCR items with both scorers (a scan script of ours, not included) found exactly one target string whose result changes: the lowercase wordmark `grawwww` of b07, whose next line is "washed black hoodie". Nothing else moves (the stacked `GRA` / `WWWW` wordmarks, `VISIT` / `NORDHAVN`, the poster and the h4 sentence give the same answer under both scorers).
- Why nothing caught it: the scorer had no unit tests; the 38 control images contain no case of a word with too few repeated letters followed by a line that starts with that letter, so c2's validity numbers are blind to it. Found by our own verification pass over the video script before publication.
- Not a bug of the readers: where c2 passes a 3-w card it is because the reader itself returned four w (Qwen-2.1, seed 101: text `grawwww`, card has three; image checked by eye).

## 2. The fix

`scripts/scoring.py` (old copy `scripts/scoring_pre_fix.py`, sha256 f40391edfdda3c512337f58e37f38f1b0e269602c3f91785e210cd7cc91dfc26; new sha256 1e53cb5b3fb7cfc87dbd1699ec414855280e225baff3605497110f45260c2ce4).

A target string (letters and digits, casefolded, exactly as before) passes when it occurs `min_count` times as a run that is either
1. inside one line, with the unchanged boundary rule (the character before the match differs from the target's first character, the character after differs from its last), or
2. across line breaks, only when the breaks split the target itself: the first part is the END of a line (same "character before" rule), every middle part is a WHOLE line, and the last part is the START of a later line that ends on a word boundary of that line (so the w of "washed" cannot complete "grawww") and is not followed, in that line, by the target's last character. Word boundaries are those of the raw line (runs of letters and digits; "AI-GENERATED" is two words). Empty lines and lines with no letter or digit are skipped, as before.

So stacked `GRA` / `WWWW` and `AI-GENERATED` / `PRESENTER` pass, the four-line chalkboard `FRESH` / `BREAD` / `DAILY` / `7AM-2PM` passes, `grawww` / `washed ...` fails. L2 strict (no casefold) is the same rule. API unchanged (`check(text, expected, fold)`); two additions: `find_runs`, and `check(..., word_aligned=True)`, the stricter sensitivity variant described in section 6.

## 3. Tests

`scripts/test_scoring.py`, stdlib `unittest`, 31 tests, run from the repository folder: `python3 -W ignore -m unittest -v scripts/test_scoring.py` -> `Ran 31 tests ... OK`.
- Group 1, the b07 Qwen case must FAIL: the inline text; the stored OCR texts of Qwen-2.1 seeds 102 and 103 and Qwen-2512 seed 101 (each also asserted PASS under the old scorer, which proves the bug on the same input); stored Krea / MOSS three-w reads; a continuation that starts a longer word (`GRAW` / `WWWASHED`) fails; four w on one line still passes (that pass is the reader's).
- Group 2, LARA / AI-GENERATED PRESENTER: both strings pass; the stored Krea b10 text passes; old and new agree on it; the first (joined) version rejected it (documented in the test); `LAR` / `AI-GENERATED...` does not produce LARA.
- Group 3, genuine splits: `GRA` / `WWWW` passes, `GRA` / `WWW` and five W fail, `GRA` / `WWWW LIME` passes, `GRA` / `WWWW WIDE` fails, `AI-GENERATED` / `PRESENTER`, a two-line sentence, the four-line sign, a wrong middle line fails, a middle part that is not a whole line fails; stored real splits (b05 `GRA` / `WWWW`, `VISIT` / `NORDHAVN`, h4 Qwen-2.1) pass.
- Unchanged definitions: casefold and punctuation, L2 strict, in-line boundary (`GRAWWWWW`), `min_count` including across breaks, `<|det|>` tags, empty text.

## 4. Re-scoring: what was run, how it was checked

1. Faithfulness check first: with the OLD scorer, our scoring scripts reproduced the old `results.json`, `results_extra.json`, `results_battery3.json` and their tables byte for byte. So the only thing that changed between the old and the new numbers is the scorer.
2. Every stored OCR output was then re-scored with the fixed scorer (every reader and arm that has an OCR output: c0, c1, c2, union, RapidOCR and the vision-model reader for the four first arms; c0, c1, c2, RapidOCR for the Qwen-Image-2.1, FIBO and Qwen-Image-2512 arms; c0, c1, c2 for Klein; the controls; the battery-3 chalkboard). A second run was byte-identical to the first.
3. The battery-3 chalkboard (h4) OCR check now uses the shared scorer (before: the target as a substring of the text with every line joined); the old pass is kept as `ocr_c2_pass_pre_fix` in `results/results_battery3.json`. Result: 12 of 12 identical.
4. Controls: sensitivity, specificity and balanced accuracy for c0, c1, c2, RapidOCR and the vision model, old and new scorer: identical lines (c2: sensitivity 20/25 = 0.80, specificity 12/13 = 0.92, balanced 0.86; c0 0.76; c1 0.68).
5. Not re-done, because no OCR scorer is involved: the AI readings and battery 2. The grids in this repository were regenerated from the new results, so their OCR PASS/FAIL stamps are the new ones.

## 5. Old -> new, in full

### 5.1 Frozen criterion (best MOSS arm per brief vs krea-dense, >= 8 of 10 briefs AND strictly fewer rerolls), old -> new

| reader | valid on controls | headline briefs MOSS >= Krea | rerolls MOSS / Krea | headline verdict | moss-prompt alone | moss-layout alone |
|---|---|---|---|---|---|---|
| **Unlimited-OCR c2 (reader of record)** | yes | 8/10 (same) | 14 / 14 -> 15 / 16 | FAIL -> PASS | 7/10, rr 19 vs 14: FAIL -> 7/10, rr 20 vs 16: FAIL | 8/10, rr 15 vs 14: FAIL -> 7/10, rr 18 vs 16: FAIL |
| Unlimited-OCR c0 | no | 10/10 (same) | 10 / 18 -> 10 / 19 | PASS (same) | 9/10, rr 18 vs 18: FAIL -> 9/10, rr 18 vs 19: PASS | 9/10, rr 13 vs 18: PASS -> 9/10, rr 13 vs 19: PASS |
| Unlimited-OCR c1 | no | 9/10 -> 8/10 | 16 / 18 -> 17 / 18 | PASS (same) | 9/10, rr 19 vs 18: FAIL -> 8/10, rr 22 vs 18: FAIL | 9/10, rr 18 vs 18: FAIL -> 8/10, rr 19 vs 18: FAIL |
| Unlimited-OCR any of c0/c1/c2 (post-hoc) | n/a | 10/10 (same) | 7 / 11 (same) | PASS (same) | 9/10, rr 14 vs 11: FAIL (same) | 8/10, rr 10 vs 11: PASS -> 7/10, rr 10 vs 11: FAIL |
| RapidOCR | no | 9/10 (same) | 5 / 14 (same) | PASS (same) | 8/10, rr 13 vs 14: PASS (same) | 8/10, rr 8 vs 14: PASS -> 7/10, rr 9 vs 14: FAIL |
| local vision model | no | 9/10 (same) | 1 / 4 -> 2 / 4 | PASS (same) | 9/10, rr 3 vs 4: PASS -> 9/10, rr 4 vs 4: FAIL | 7/10, rr 3 vs 4: FAIL -> 7/10, rr 4 vs 4: FAIL |
| AI reading | n/a | 9/10 (same) | 1 / 3 (same) | PASS (same) | 9/10, rr 1 vs 3: PASS (same) | 6/10, rr 5 vs 3: FAIL (same) |

Best-of-MOSS against krea-ie on b01-b05 (c2): 4/5 (same).

Per brief, reader of record c2, headline comparison (only the rows that changed):

| brief | MOSS best rate / rerolls | Krea rate / rerolls |
|---|---|---|
| b07-endcard-hoodie | 1.0 / 0 -> 0.33 / 1 | 1.0 / 0 -> 0.33 / 2 |

### 5.2 Images passing out of 30, reader of record c2 (krea-ie out of 15), with rerolls and briefs with no pass in 3 seeds (censored), old -> new

| arm | images passing | rerolls total | censored briefs |
|---|---|---|---|
| krea-dense | 12/30 -> 10/30 | 14 -> 16 | 4 (same) |
| krea-ie | 3/15 (same) | 12 (same) | 4 (same) |
| moss-prompt | 9/30 -> 7/30 | 19 -> 20 | 6 (same) |
| moss-layout | 11/30 -> 8/30 | 15 -> 18 | 3 -> 4 |
| qwen21 | 9/30 -> 7/30 | 20 (same) | 6 (same) |
| fibo | 13/30 -> 12/30 | 16 (same) | 5 (same) |
| qwena | 6/30 -> 5/30 | 20 -> 22 | 6 (same) |
| klein | 11/30 -> 10/30 | 16 -> 17 | 4 (same) |

### 5.3 Agreement of each OCR reader with the AI reading (images where both say pass or both say fail), old -> new

| reader | frozen four arms (105 images) | extra arms qwen21 + fibo + qwena (90 images) | klein (30 images) | c2 sens / spec on the 105 |
|---|---|---|---|---|
| unl_c2 | 49/105 -> 48/105 | 49/90 -> 51/90 | 11/30 -> 10/30 | 0.376 / 0.85 -> 0.329 / 1.0 |
| unl_c0 | 49/105 (same) | 52/90 -> 56/90 | 11/30 -> 10/30 |  |
| unl_c1 | 45/105 -> 44/105 | 49/90 -> 51/90 | 13/30 -> 11/30 |  |
| unl_any | 62/105 -> 63/105 | not run | not run |  |
| rapid | 62/105 -> 64/105 | 64/90 -> 65/90 | not run |  |
| vlm | 91/105 -> 92/105 | not run | not run |  |

c2 per extra arm: qwen21 13/30 -> 15/30; fibo 23/30 -> 22/30; qwena 13/30 -> 14/30; klein 11/30 -> 10/30.
All 225 images (105 + 90 + 30), c2 against the AI reading: 109/225 -> 109/225.

### 5.4 b07 end card ("grawwww", AI reading 4 w for Krea, MOSS, FIBO, Klein; 3 w for both Qwens), seed 101, per arm and reader, old -> new

PASS/FAIL of the whole card (all three strings). c2 text = what the reader of record returned for the wordmark and the next line.

| arm | AI reading | c2 | c0 | c1 | RapidOCR | c2 text (first lines) |
|---|---|---|---|---|---|---|
| krea-dense | PASS (same) | PASS -> FAIL | PASS -> FAIL | PASS (same) | FAIL (same) | `grawww / washed black hoodie / AI-generated · fictional model and bran` |
| moss-prompt | PASS (same) | PASS -> FAIL | PASS (same) | PASS -> FAIL | PASS (same) | `grawww / washed black hoodie / AI-generated · fictional model and bran` |
| moss-layout | FAIL (same) | PASS -> FAIL | PASS (same) | PASS -> FAIL | PASS -> FAIL | `grawww / grawww / washed black hoodie / AI-generated · fictional model` |
| qwen21 | FAIL (same) | PASS (same) | PASS -> FAIL | PASS -> FAIL | PASS -> FAIL | `grawwww / washed black hoodie / www.ucan.com / AI-generated • fictiona` |
| fibo | PASS (same) | FAIL (same) | FAIL (same) | FAIL (same) | FAIL (same) | `grawwww / washed black hoodle /  / AI-generated • fictional model and ` |
| qwena | FAIL (same) | PASS -> FAIL | PASS -> FAIL | PASS -> FAIL | FAIL (same) | `grawww / washed black hoodie / AI generated · fictional model and bran` |
| klein | PASS (same) | PASS -> FAIL | PASS (same) | PASS -> FAIL | n/a | `grawww / washed black hoodie / AI-generated • fictional model and bran` |

b07, all seeds, reader of record c2 (images passing out of 3): krea-dense 3 -> 1; moss-prompt 3 -> 1; moss-layout 3 -> 0; qwen21 3 -> 1; fibo 2 -> 1; qwena 2 -> 1; klein 3 -> 2.

Hoodie images the AI reading counted as 3 w (Qwen-2.1 and Qwen-2512, briefs b01, b02, b07 x 3 seeds = 9 each) that each OCR reader PASSED, old -> new:

| arm | c2 | c0 | c1 | RapidOCR |
|---|---|---|---|---|
| qwen21 | 3/9 -> 1/9 | 3/9 -> 0/9 | 2/9 -> 0/9 | 1/9 -> 0/9 |
| qwena | 2/9 -> 1/9 | 1/9 -> 0/9 | 1/9 -> 0/9 | 0/9 (same) |

### 5.5 Battery 3, h4 chalkboard ("FRESH BREAD DAILY 7AM-2PM"), OCR c2 pass, old -> new

Old rule = `GOAL in norm(text)` on the joined text (what wrote the old `results_battery3.json`). New = shared `scoring.check` (one line, or a break that splits the target, continuation a whole word).

| model | seed 101 | seed 102 | AI reading |
|---|---|---|---|
| krea-dense | FAIL (same) | FAIL (same) | PASS / PASS |
| moss-prompt | FAIL (same) | FAIL (same) | PASS / PASS |
| qwen21 | PASS (same) | PASS (same) | PASS / PASS |
| fibo | FAIL (same) | PASS (same) | PASS / PASS |
| qwena | PASS (same) | PASS (same) | FAIL / FAIL |
| klein | PASS (same) | PASS (same) | PASS / PASS |

Changed h4 images: 0 of 12. Battery-3 totals by the AI reading (the headline of that battery) are not touched by any OCR scorer.

### 5.6 Reader validity on the controls (pre-declared bar: sensitivity >= 0.80 and specificity >= 0.90) and configuration choice, old -> new

| reader | sens | spec | valid | balanced accuracy |
|---|---|---|---|---|
| unl_c0 | 0.6 (same) | 0.923 (same) | NO (same) | 0.76 (same) |
| unl_c1 | 0.52 (same) | 0.846 (same) | NO (same) | 0.68 (same) |
| unl_c2 | 0.8 (same) | 0.923 (same) | yes (same) | 0.86 (same) |
| rapid | 0.72 (same) | 1.0 (same) | NO (same) | 0.86 (same) |
| vlm | 0.88 (same) | 0.769 (same) | NO (same) | 0.82 (same) |

Every control image scores the same under the old and the new scorer (scan of every stored OCR item with both scorers: 190 control items, 0 changed), so c2 is still the configuration with the highest balanced accuracy among the three Unlimited-OCR configurations (0.86 against 0.76 and 0.68) and is still valid. The controls hold no case like b07 (a word with too few repeated letters followed by a line that starts with that letter), which is why they could not have caught the bug.

### 5.7 Every image whose result changed, by reader (old pass -> new FAIL; nothing changed in the other direction)

| reader | images changed | files |
|---|---|---|
| unl_c2 | 12 | `b07-endcard-hoodie_krea-dense_101` PASS->FAIL, `b07-endcard-hoodie_krea-dense_102` PASS->FAIL, `b07-endcard-hoodie_moss-prompt_101` PASS->FAIL, `b07-endcard-hoodie_moss-prompt_103` PASS->FAIL, `b07-endcard-hoodie_moss-layout_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_102` PASS->FAIL, `b07-endcard-hoodie_moss-layout_103` PASS->FAIL, `b07-endcard-hoodie_qwen21_102` PASS->FAIL, `b07-endcard-hoodie_qwen21_103` PASS->FAIL, `b07-endcard-hoodie_fibo_103` PASS->FAIL, `b07-endcard-hoodie_qwena_101` PASS->FAIL, `b07-endcard-hoodie_klein_101` PASS->FAIL |
| unl_c0 | 7 | `b07-endcard-hoodie_krea-dense_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_103` PASS->FAIL, `b07-endcard-hoodie_qwen21_101` PASS->FAIL, `b07-endcard-hoodie_qwen21_102` PASS->FAIL, `b07-endcard-hoodie_qwen21_103` PASS->FAIL, `b07-endcard-hoodie_qwena_101` PASS->FAIL, `b07-endcard-hoodie_klein_103` PASS->FAIL |
| unl_c1 | 11 | `b07-endcard-hoodie_moss-prompt_101` PASS->FAIL, `b07-endcard-hoodie_moss-prompt_102` PASS->FAIL, `b07-endcard-hoodie_moss-prompt_103` PASS->FAIL, `b07-endcard-hoodie_moss-layout_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_103` PASS->FAIL, `b07-endcard-hoodie_qwen21_101` PASS->FAIL, `b07-endcard-hoodie_qwen21_102` PASS->FAIL, `b07-endcard-hoodie_fibo_103` PASS->FAIL, `b07-endcard-hoodie_qwena_101` PASS->FAIL, `b07-endcard-hoodie_klein_101` PASS->FAIL, `b07-endcard-hoodie_klein_103` PASS->FAIL |
| unl_any | 1 | `b07-endcard-hoodie_moss-layout_103` PASS->FAIL |
| rapid | 3 | `b07-endcard-hoodie_moss-layout_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_103` PASS->FAIL, `b07-endcard-hoodie_qwen21_101` PASS->FAIL |
| vlm | 3 | `b07-endcard-hoodie_moss-prompt_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_101` PASS->FAIL, `b07-endcard-hoodie_moss-layout_103` PASS->FAIL |

Images that went from FAIL to PASS under the fixed scorer: 0.

### 5.8 Frozen rule applied to the extra arms (information only, never a verdict of record), where the reading changed

| arm | reader | against | old | new |
|---|---|---|---|---|
| qwen21 | unl_c2 | krea-dense | 7/10, rr 20 vs 14: FAIL | 7/10, rr 20 vs 16: FAIL |
| qwen21 | unl_c2 | moss-prompt | 8/10, rr 20 vs 19: FAIL | 8/10, rr 20 vs 20: FAIL |
| qwen21 | unl_c2 | best-of-MOSS | 5/10, rr 20 vs 14: FAIL | 5/10, rr 20 vs 15: FAIL |
| qwen21 | unl_c0 | krea-dense | 9/10, rr 20 vs 18: FAIL | 8/10, rr 23 vs 19: FAIL |
| qwen21 | unl_c0 | moss-prompt | 8/10, rr 20 vs 18: FAIL | 7/10, rr 23 vs 18: FAIL |
| qwen21 | unl_c0 | best-of-MOSS | 6/10, rr 20 vs 10: FAIL | 5/10, rr 23 vs 10: FAIL |
| qwen21 | unl_c1 | krea-dense | 8/10, rr 21 vs 18: FAIL | 8/10, rr 24 vs 18: FAIL |
| qwen21 | unl_c1 | moss-prompt | 8/10, rr 21 vs 19: FAIL | 9/10, rr 24 vs 22: FAIL |
| qwen21 | unl_c1 | best-of-MOSS | 6/10, rr 21 vs 16: FAIL | 6/10, rr 24 vs 17: FAIL |
| qwen21 | rapid | krea-dense | 5/10, rr 18 vs 14: FAIL | 5/10, rr 21 vs 14: FAIL |
| qwen21 | rapid | moss-prompt | 6/10, rr 18 vs 13: FAIL | 6/10, rr 21 vs 13: FAIL |
| qwen21 | rapid | best-of-MOSS | 4/10, rr 18 vs 5: FAIL | 4/10, rr 21 vs 5: FAIL |
| fibo | unl_c2 | krea-dense | 6/10, rr 16 vs 14: FAIL | 7/10, rr 16 vs 16: FAIL |
| fibo | unl_c2 | moss-prompt | 8/10, rr 16 vs 19: PASS | 9/10, rr 16 vs 20: PASS |
| fibo | unl_c2 | best-of-MOSS | 6/10, rr 16 vs 14: FAIL | 7/10, rr 16 vs 15: FAIL |
| fibo | unl_c0 | krea-dense | 8/10, rr 16 vs 18: PASS | 9/10, rr 16 vs 19: PASS |
| fibo | unl_c1 | krea-dense | 8/10, rr 21 vs 18: FAIL | 8/10, rr 21 vs 18: FAIL |
| fibo | unl_c1 | moss-prompt | 8/10, rr 21 vs 19: FAIL | 9/10, rr 21 vs 22: PASS |
| fibo | unl_c1 | best-of-MOSS | 6/10, rr 21 vs 16: FAIL | 7/10, rr 21 vs 17: FAIL |
| qwena | unl_c2 | krea-dense | 6/10, rr 20 vs 14: FAIL | 7/10, rr 22 vs 16: FAIL |
| qwena | unl_c2 | moss-prompt | 6/10, rr 20 vs 19: FAIL | 7/10, rr 22 vs 20: FAIL |
| qwena | unl_c2 | best-of-MOSS | 4/10, rr 20 vs 14: FAIL | 5/10, rr 22 vs 15: FAIL |
| qwena | unl_c0 | krea-dense | 8/10, rr 21 vs 18: FAIL | 8/10, rr 24 vs 19: FAIL |
| qwena | unl_c0 | moss-prompt | 7/10, rr 21 vs 18: FAIL | 7/10, rr 24 vs 18: FAIL |
| qwena | unl_c0 | best-of-MOSS | 3/10, rr 21 vs 10: FAIL | 3/10, rr 24 vs 10: FAIL |
| qwena | unl_c1 | krea-dense | 8/10, rr 19 vs 18: FAIL | 8/10, rr 22 vs 18: FAIL |
| qwena | unl_c1 | moss-prompt | 7/10, rr 19 vs 19: FAIL | 8/10, rr 22 vs 22: FAIL |
| qwena | unl_c1 | best-of-MOSS | 6/10, rr 19 vs 16: FAIL | 6/10, rr 22 vs 17: FAIL |
| klein | unl_c2 | krea-dense | 7/10, rr 16 vs 14: FAIL | 7/10, rr 17 vs 16: FAIL |
| klein | unl_c2 | moss-prompt | 8/10, rr 16 vs 19: PASS | 8/10, rr 17 vs 20: PASS |
| klein | unl_c2 | best-of-MOSS | 5/10, rr 16 vs 14: FAIL | 5/10, rr 17 vs 15: FAIL |
| klein | unl_c0 | krea-dense | 9/10, rr 17 vs 18: PASS | 9/10, rr 17 vs 19: PASS |
| klein | unl_c0 | moss-prompt | 9/10, rr 17 vs 18: PASS | 8/10, rr 17 vs 18: PASS |
| klein | unl_c0 | best-of-MOSS | 5/10, rr 17 vs 10: FAIL | 4/10, rr 17 vs 10: FAIL |
| klein | unl_c1 | krea-dense | 10/10, rr 14 vs 18: PASS | 9/10, rr 15 vs 18: PASS |
| klein | unl_c1 | moss-prompt | 10/10, rr 14 vs 19: PASS | 10/10, rr 15 vs 22: PASS |
| klein | unl_c1 | best-of-MOSS | 9/10, rr 14 vs 16: PASS | 9/10, rr 15 vs 17: PASS |

## 6. Caveats

- **The flip is thin and comes from reader errors.** The new verdict rests on one reroll (15 vs 16) on one brief (b07). On b07, c2 now fails Krea 101 and 102, MOSS-prompt 101 and 103, Klein 101 and FIBO 103 because it returned `grawww` (three w) for cards the AI reading counts as four; it is an undercounting reader, not a measure of the images. (For MOSS-layout b07, where the AI reading says 0 of 3, the fix moves c2 from 3/3 to 0/3, the AI reading's number.) The reader agrees with the AI reading on 48 of 105 images. Both facts should travel with the verdict wherever it is quoted. The criterion is not moved: the rule was written before the run, and applied as written it now reads MET.
- **Before/after, both reported.** Addendum 3 is a bug fix made after seeing results; the old numbers are kept and shown next to the new ones, and every reader is re-scored, not only the one whose verdict moved.
- **One property kept on purpose.** Inside one line L1 ignores spaces, so `grawww washed black hoodie` on a single line would still read as `grawwww`. No stored OCR text has this: the stricter variant (`check(..., word_aligned=True)`: matches must start and end on word boundaries) differs from the fixed rule on 0 of 1 177 items (our scan). It is tested (`test_same_line_spans_a_space_by_definition...`) and left as defined in PREREG.
- **The pinned scorer hash.** `PREREG.md` pins sha256 7c200ff6... (the first, joined version, `scripts/scoring_v1.py`). The scores of record were made by the line-aware version (f40391ed...); the scorer in force is 1e53cb5b.... Addendum 3 says so.
- **A lone `w` line counts.** By the rule as written the continuation may be a whole word, so `grawww` followed by a line that is just `w` passes. No stored text has it.
- **New brief strings.** Any new target whose last letter can begin the next line of a card needs a unit test before it is scored.
