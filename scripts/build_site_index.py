#!/usr/bin/env python3
"""Build a compact site index from per-paper analysis JSON files."""

from __future__ import annotations

import json
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_PATH = REPO_ROOT / "data" / "index.json"

COLLECTIONS = [
    {
        "key": "cvpr2025_first10",
        "label": "CVPR 2025 First 10",
        "dir": REPO_ROOT / "analyses" / "cvpr2025_first10",
        "priority": 3,
    },
    {
        "key": "cvpr2025_diffusion",
        "label": "CVPR 2025 Diffusion",
        "dir": REPO_ROOT / "analyses" / "cvpr2025_diffusion",
        "priority": 2,
    },
    {
        "key": "cvpr2025_diffusion_transformer_video",
        "label": "Diffusion Transformer / Video Diffusion",
        "dir": REPO_ROOT / "analyses" / "cvpr2025_diffusion_transformer_video",
        "priority": 1,
    },
]


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


def merge_record(record: dict, data: dict, collection: dict) -> None:
    record["collections"].append(collection["label"])
    record["collection_keys"].append(collection["key"])
    record["source_paths"][collection["key"]] = f"analyses/{collection['key']}/{record['paper_id']}.json"
    record["priorities"].append(collection["priority"])

    current_priority = min(record["priorities"])
    if collection["priority"] == current_priority:
        record["primary_collection"] = collection["label"]
        record["primary_collection_key"] = collection["key"]
        record["detail_path"] = (
            f"paper.html?id={record['paper_id']}&collection={collection['key']}"
        )
        record["generated_at"] = data["generated_at"]
        record["page_count"] = data["source"].get("page_count", 0)
        record["source_filename"] = data["source"]["filename"]
        record["story_summary"] = short_text(data["core_story"].get("summary", ""), 240)
        record["problem"] = short_text(data["core_story"].get("problem", ""), 180)
        record["proposed_method"] = short_text(data["core_story"].get("proposed_method", ""), 180)
        record["notable_sentence"] = short_text((data.get("notable_sentences") or [""])[0], 180)
        record["intro_paragraphs"] = len(data.get("introduction_structure", []))
        record["method_sections"] = len(data.get("method_structure", []))
        record["experiment_sections"] = len(data.get("experiment_structure", []))
        record["template_counts"] = {
            key: len(value) for key, value in data.get("writing_templates", {}).items()
        }


def build_index() -> dict:
    merged: dict[str, dict] = {}
    collection_labels = []
    for collection in COLLECTIONS:
        if not collection["dir"].exists():
            continue
        collection_labels.append(collection["label"])
        for path in sorted(collection["dir"].glob("*.json")):
            if path.name.startswith("_"):
                continue
            data = load_record(path)
            paper_id = data["paper_id"]
            if paper_id not in merged:
                merged[paper_id] = {
                    "paper_id": paper_id,
                    "paper_title": data["paper_title"],
                    "theme": guess_theme(data["paper_title"]),
                    "collections": [],
                    "collection_keys": [],
                    "source_paths": {},
                    "priorities": [],
                    "detail_path": "",
                    "primary_collection": "",
                    "primary_collection_key": "",
                    "generated_at": "",
                    "page_count": 0,
                    "source_filename": "",
                    "story_summary": "",
                    "problem": "",
                    "proposed_method": "",
                    "notable_sentence": "",
                    "intro_paragraphs": 0,
                    "method_sections": 0,
                    "experiment_sections": 0,
                    "template_counts": {},
                }
            merge_record(merged[paper_id], data, collection)

    records = sorted(merged.values(), key=lambda item: item["paper_title"].lower())
    themes = sorted({record["theme"] for record in records})
    return {
        "site": {
            "title": "Elephant Paper Reading",
            "subtitle": "Writing-pattern notes from CVPR 2025 papers",
            "dataset": "CVPR 2025 Collections",
        },
        "stats": {
            "paper_count": len(records),
            "theme_count": len(themes),
            "collection_count": len(collection_labels),
        },
        "themes": themes,
        "collections": collection_labels,
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
