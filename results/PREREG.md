# Pre-registration (written 2026-10-20 16:30 UTC, before any test image was generated)

> Publication note: this is the working document, copied here with internal file paths and project names removed (the lines that changed are the ones that named
> a ticket file, a script of ours that is not in this repository, or a path). The rules, the numbers and the dates are unchanged. File names that point to
> `ocr/`, `controls/`, `images/`, `episode/` or `results.*` refer to the original working folder: the published equivalents are in `results/` and `prompts/`.
> Addendum 3 (2026-10-22) records a bug fix in our scorer and changes the verdict of record: read it, and `SCORER-FIX.md`, before quoting any number from this file.

Frozen test plan. Its criterion is not changed afterwards: this file only fixes how the criterion's words are measured, so that the numbers cannot be chosen after the results are seen.

## Test set
10 briefs from our own past productions, fictional brands only, no faces, no private LoRA: `spec/briefs.json`, published as `prompts/briefs.json`
(the file used had sha256 f351defff3c85b119f63b3632fdd497112cbab0350d757313185c5863a9d2ccc; the published copy only has its 'source' and 'ie.ref' fields reworded, see its 'note').
Canvas 1024x1792 for every arm, seeds 101, 102, 103 (same seed values in every arm; the models are different, so a seed is a repeat, not a pairing).

## Arms (the four of the plan)
| id | what | settings |
|---|---|---|
| krea-dense | Krea 2 Turbo (fp8) text-to-image, no LoRA, the brief's dense prompt | 9 steps, er_sde/beta, cfg 1, qwen_image_vae (our standard graph) |
| krea-ie | Krea 2 Turbo + Identity Edit v1.2, the pack shot as the single reference, scene in text | 10 steps, euler/simple, cfg 1, ref_boost 4, grounding 768, fit. Only for briefs that have a pack shot (b01-b05). The other five briefs are typography or multi-product: arm not applicable, not swapped for anything else |
| moss-prompt | MOSS-Image SFT int8 convrot + Qwen3.5-9B int8 convrot encoder, the SAME dense prompt as krea-dense, raw (prompt upsampler OFF) | OpenMOSS README defaults: 50 steps, cfg 3.0, euler/simple, shift 5 (model default), skip-layer guidance on layer 22 (negative branch, whole schedule), vendor negative "nsfw, worst quality, bad anatomy, watermark, jpeg artifact", FLUX.2 small decoder |
| moss-layout | same as moss-prompt, but the prompt is the layout JSON (summary.caption + items with bboxes and text), written once per brief by hand | boxes converted exactly like ComfyUI's MOSSImageLayoutPrompt node |

Not measured: MOSS with the prompt upsampler on; the ComfyUI template's faster settings (25 steps, er_sde) beyond a speed probe on two throw-away calibration prompts.
Layouts were written once, before generation, and are not tuned per result.

## OCR gate (Unlimited-OCR, MIT)
baidu/Unlimited-OCR, run locally (transformers 4.57.1, torch 2.10.0, greedy, "gundam" config). Gate controls (rendered text, correct and one-character-wrong strings, and the
real pack shots, `controls/`) are run first: a gate that passes a wrong string or fails a right one is reported as such.
Match rule = `scripts/scoring.py` (sha256 7c200ff6...a66854): L1 primary = NFKC, letters and digits only, casefolded, whole-run match, `min_count` occurrences;
L2 strict = same without casefolding. An image passes a brief only if all its label strings pass (image-level). Punctuation (middle dot, hyphen) is not scored.
RapidOCR (Apache-2.0, CPU) is a cross-check only. The agent visual reading (an AI model, not a person) of every image is a third check; where it disagrees with the gate, both are reported and the primary number stays the gate's.

## Metrics
- Exact-match rate per brief and arm = passing images / 3 (image-level, L1). String-level rates are reported too.
- Rerolls per brief and arm = number of failing images before the first passing one, taking the seeds in order 101, 102, 103; a brief with no pass in 3 seeds counts 3 (censored, flagged). "Fewer rerolls" = strictly lower total over the 10 briefs.
- Seconds per image = ComfyUI execution_start to execution_success (ms timestamps from /history); the first image after an arm switch is flagged cold (model load) and reported separately.
- Peak VRAM = whole card, nvidia-smi 0.5 s samples during each image, plus the peak of the whole job.

## How the frozen criterion is read (the wording is ambiguous on which MOSS arm and which Krea arm)
"exact-match rate of label text >= the Krea arm on >= 8 of 10 briefs and fewer rerolls":
- HEADLINE: per brief, the better of the two MOSS arms (the system as we would use it: prompt-only, or layout when it helps) against krea-dense (the arm that exists for all ten briefs; it is what we generate with today). Pass = MOSS rate >= Krea rate on >= 8 of 10 briefs AND total MOSS rerolls < total Krea rerolls.
- Also reported, same rule, no change of target: each MOSS arm alone vs krea-dense; and both against krea-ie on b01-b05 (where it exists). The Identity Edit arm copies the pack shot, so it is the ceiling for "keep this exact label"; the plan keeps identity editing separate, so it does not decide the headline.
- AI-slop look-check: the agent visual reading (an AI model looking at the images, not a person; a person's review of the grids is still to happen), subjective, from every contact sheet; it can veto "MOSS joins" in the recommendation but does not change the numeric verdict.

## Addendum 1 (2026-10-20, written after the calibration session `t004-calib-20261020T163526Z` and before the first test image; no test image existed)
What the calibration showed (files: `ocr/controls_unlimited_doc.json`, `ocr/calib_unlimited_doc.json`, `results_gen.jsonl` phase calib):
- Unlimited-OCR is a document parser: its only documented prompt is `<image>document parsing.`. The prompt `Free OCR.` returns junk (sensitivity 5/16 on the controls). In document mode it labels most photographs as an `image` block and returns no text:
  on 4 real pack shots it returned nothing or `GIRA MIM LIME`; on 5 generated photos of a bottle label (agent visual reading: all five labels are correct) it read 2 of 5.
  On 16 rendered positives it passed 8, on 12 rendered one-letter-wrong negatives it rejected 11. It also miscounts repeated letters (GRA/WWWW read as GRA/WWW; five W's read as four).
- The wordmark on a can wraps around it: the pack shots themselves show the W row clipped by the can's curve, so a strict "GRAWWWW" is not fully visible on any can photo, including the Identity Edit copy of the pack shot (`images_calibration/ie_smoke_b03_krea-ie_11.png`).
- `scoring.py` joined OCR lines into one string and so rejected LARA + AI-GENERATED PRESENTER; it is now line-aware (old copy `scripts/scoring.py.bak-2026-10-20-prereg`). Same definition of the metric, bug fix only.
- MOSS speed probe (calibration prompts, not test): official settings 27.2-27.6 s warm (cold 37.2 s), peak 15.6-18.6 GB whole card; template settings 14.0 s warm. Settings of the test stay the vendor's (50 steps).
Decisions fixed now:
1. Unlimited-OCR is run in three configurations (`scripts/ocr_run.py`: c0 whole image gundam, c1 whole image base, c2 overlapping bands). The configuration is chosen on controls only: highest balanced accuracy (sensitivity + specificity) on `controls/` (28 rendered and real pack-shot images) plus `controls_real/` (10 generated photos/posters with the agent visual reading as truth); ties go to the lower id. No test image is used to choose.
2. Gate validity: a reader whose sensitivity on the truth-positive controls is below 0.80, or whose specificity on the truth-negative controls is below 0.90, is declared NOT VALID for this task. The frozen-gate verdict is still computed and reported mechanically. The verdict of record is then taken from the first valid reader in this order: (a) Unlimited-OCR, (b) the local vision model transcribing the text (`scripts/vlm_reader.py`, validated the same way), (c) the agent visual reading of every image (an AI model's own look, zoomed crops where the text is small; not a person), recorded in `ocr/agent_reading.json`. The report says which reader the verdict rests on and shows the others.
3. For the clipped can wordmark, the agent visual reading counts a W as present if its glyph is visible even when partly clipped by the can's edge; the OCR readers cannot do that, which is one more reason they are cross-checks here.
4. Everything else in this file stands.

## Addendum 2 (2026-10-20, after scoring; wording fixes and how the verdict of record was taken)
- Relabel: every earlier "human" or "my reading" in this file, in the scripts, in `results.*` and in the grids means the agent visual reading: an AI model (an AI agent) looking at the images. No person had reviewed the images when this was written; a person's review of the grids came before publishing.
- Addendum 1 applied exactly as written. Gate configuration chosen on controls only: c2 (bands) has the highest balanced accuracy on `controls/` + `controls_real/` (0.86 vs 0.76 for c0 and 0.68 for c1). Validity by the thresholds: c2 sensitivity 20/25 = 0.80 (not below 0.80) and specificity 12/13 = 0.92: VALID. c0, c1, RapidOCR (sens 0.72) and the vision-model reader (spec 0.77) are NOT VALID. The verdict of record is therefore the mechanical verdict of Unlimited-OCR c2. The other readers' verdicts are shown next to it in `results_tables.md` and none is chosen over it.
- Observation, not a rule change: after scoring, the agent visual reading disagrees with the c2 gate on 56 of the 105 test images (c2 passes 32 of the 85 images the agent judged correct). That is reported in `results_tables.md`; it does not change the verdict of record.

## Addendum 3 (2026-10-22, after scoring and after the first reports; scorer BUG FIX, same metric definition; both sets of numbers are reported in `SCORER-FIX.md`, next to this file)
- **What was wrong.** The line-aware `scripts/scoring.py` introduced in Addendum 1 (sha256 f40391ed...1dfc26, kept as `scripts/scoring_pre_fix.py`) let a match cross a line break at ANY position of the target and complete it with the first letter of the NEXT line, even when that letter began an unrelated word. On the b07 card a reader text "grawww" followed by the line "washed black hoodie" counted as "grawwww": the w of "washed" was taken as the fourth w. That pass belonged to the scorer, not to the reader. Found by our own verification pass over the video script before publication.
- **The fix.** A target must match inside one line, or across line breaks only when the breaks split the target itself: the first part is the end of a line, every middle part is a whole line, and the last part is the start of a later line that ends on a word boundary of that line (the continuation must not be the beginning of a longer word). The L1 normalisation (NFKC, letters and digits only, casefold), the whole-run boundary rule inside a line (the character before the match differs from the target's first character, the character after differs from its last), `min_count`, L2 strict (no casefold), image-level pass and every reader, threshold and criterion are unchanged. Fixed scorer: sha256 1e53cb5b...0c2ce4. Unit tests: `scripts/test_scoring.py` (31 tests: the b07 Qwen case fails; "LARA" / "AI-GENERATED PRESENTER" still passes; stacked GRA / WWWW and a four-line sign pass; run with `python3 -m unittest scripts/test_scoring.py` from the repository folder). The h4 chalkboard OCR check of battery 3 now uses the same scorer (before: the target as a substring of the text with every line joined); its 12 results are identical under both rules.
- **No other rule changed, no number was chosen.** Controls: every control OCR item scores identically (190 items, 0 changed), so the selection of c2 on controls (balanced accuracy 0.86 against 0.76 and 0.68) and its validity (sensitivity 20/25 = 0.80, specificity 12/13 = 0.92) are the same. Re-scoring every stored OCR output (975 label items, 190 control items, 12 h4 items; a scan script of ours, not included): only the target string "grawwww" (b07) changes; 36 image-level results across all readers go from pass to fail, none the other way.
- **Consequence for the verdict of record, computed by the rule exactly as written in "How the frozen criterion is read".** Reader of record c2, best MOSS arm per brief against krea-dense: briefs MOSS >= Krea 8 of 10 (unchanged), total rerolls MOSS 15 against Krea 16 (was 14 against 14). "Fewer rerolls" is strictly lower, so the criterion reads MET (was NOT MET, by a tie). The margin is one reroll on three seeds per cell, and the reader of record agrees with the AI reading on only 48 of 105 images; both facts are stated wherever the verdict is quoted. Each MOSS arm alone still FAILS (moss-prompt 7/10, rerolls 20 against 16; moss-layout 7/10, rerolls 18 against 16). The verdict printed in our first report is superseded; the old numbers are kept next to the new ones in `SCORER-FIX.md`.
- **What did not change.** The AI reading (every number), battery 2, battery 3 totals, the controls, the readers' validity, the images. The agreement of the reader of record with the AI reading goes from 49/105 to 48/105 on the four frozen arms, 49/90 to 51/90 on Qwen-2.1, FIBO and Qwen-2512, and 11/30 to 10/30 on Klein.
- **A note on pinned files.** The "Match rule" line above pins sha256 7c200ff6...a66854, the first (joined) version that never scored a test image; the scores of record were made with the line-aware version of Addendum 1 (the sha256 given above), and the scorer in force is now the fixed one.
