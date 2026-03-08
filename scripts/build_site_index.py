#!/usr/bin/env python3
"""Build a compact site index from per-paper analysis JSON files."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = REPO_ROOT / "analyses" / "cvpr2025_first10"
OUTPUT_PATH = REPO_ROOT / "data" / "index.json"


def load_record(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def short_text(text: str, limit: int = 220) -> str:
    clean = " ".join((text or "").split())
    if len(clean) <= limit:
        return clean
    return clean[: limit - 1].rstrip() + "..."


def guess_theme(title: str) -> str:
    title_lower = title.lower()
    if "3d" in title_lower:
        return "3D Vision"
    if "diffusion" in title_lower:
        return "Diffusion"
    if "mamba" in title_lower:
        return "Mamba"
    if "language" in title_lower or "llm" in title_lower or "llava" in title_lower:
        return "Multimodal"
    return "General CV"


def build_index() -> dict:
    records = []
    for path in sorted(ANALYSIS_DIR.glob("*.json")):
        if path.name.startswith("_"):
            continue
        data = load_record(path)
        records.append(
            {
                "paper_id": data["paper_id"],
                "paper_title": data["paper_title"],
                "detail_path": f"paper.html?id={data['paper_id']}",
                "dataset": "CVPR 2025 First 10",
                "theme": guess_theme(data["paper_title"]),
                "generated_at": data["generated_at"],
                "page_count": data["source"].get("page_count", 0),
                "source_filename": data["source"]["filename"],
                "story_summary": short_text(data["core_story"].get("summary", ""), 240),
                "problem": short_text(data["core_story"].get("problem", ""), 180),
                "proposed_method": short_text(data["core_story"].get("proposed_method", ""), 180),
                "notable_sentence": short_text((data.get("notable_sentences") or [""])[0], 180),
                "intro_paragraphs": len(data.get("introduction_structure", [])),
                "method_sections": len(data.get("method_structure", [])),
                "experiment_sections": len(data.get("experiment_structure", [])),
                "template_counts": {
                    key: len(value)
                    for key, value in data.get("writing_templates", {}).items()
                },
            }
        )

    themes = sorted({record["theme"] for record in records})
    return {
        "site": {
            "title": "Elephant Paper Reading",
            "subtitle": "Writing-pattern notes from CVPR 2025 papers",
            "dataset": "CVPR 2025 First 10",
        },
        "stats": {
            "paper_count": len(records),
            "theme_count": len(themes),
        },
        "themes": themes,
        "papers": records,
    }


def main() -> int:
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = build_index()
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)
    print(f"wrote {OUTPUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
