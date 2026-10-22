"""Where things live. Every script imports this.

ROOT     the repository folder
PROMPTS  ROOT/prompts: the briefs, the battery-2 prompts, the FIBO captions, the reader controls (published, read-only inputs)
WORK     the folder the scripts read generated images and raw reader output from, and log runs in. Default ROOT/runs (git-ignored).
         Set T004_WORK to use another folder. Layout inside it:
           images/<brief>_<arm>_<seed>.png            krea-dense, krea-ie, moss-prompt, moss-layout
           images/<arm>/<brief>_<arm>_<seed>.png      qwen21, fibo, qwena
           images/battery2/<arm>/<prompt>_<arm>_<seed>.png
           ocr/...                                    raw reader output (see final_score.py and score_extra.py for the file names)
           results_gen.jsonl, results_extra.jsonl, results_fibo.jsonl, results_battery2.jsonl     one line per image: time, VRAM
OUT      where the scoring scripts write results.json, results_extra.json, results_battery2.json and the tables. Default ROOT/results
         (the published copies). Set T004_OUT to write somewhere else.
"""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROMPTS = ROOT / "prompts"
WORK = Path(os.environ.get("T004_WORK") or ROOT / "runs")
OUT = Path(os.environ.get("T004_OUT") or ROOT / "results")


def find_font(name):
    """Path of a DejaVu Sans font file (used for the grids and the rendered controls). Set T004_FONT_DIR if yours is somewhere else."""
    import sys
    for d in [os.environ.get("T004_FONT_DIR"), "/usr/share/fonts/truetype/dejavu", "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF", "/Library/Fonts", "C:/Windows/Fonts"]:
        if d and (Path(d) / name).exists():
            return str(Path(d) / name)
    sys.exit(f"{name} not found: install DejaVu Sans (Debian/Ubuntu: fonts-dejavu-core) or set T004_FONT_DIR")
