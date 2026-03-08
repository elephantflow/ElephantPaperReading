#!/usr/bin/env python3
"""Batch paper-writing analysis for local PDF folders.

This script extracts text with pypdf, heuristically segments key sections,
and writes one JSON analysis file per paper.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from pypdf import PdfReader


SECTION_PATTERNS = {
    "abstract": [
        r"\babstract\b",
    ],
    "introduction": [
        r"\b\d+\.?\s+introduction\b",
        r"\bintroduction\b",
    ],
    "related_work": [
        r"\b\d+\.?\s+related work\b",
        r"\b\d+\.?\s+background\b",
        r"\b\d+\.?\s+preliminar(?:y|ies)\b",
    ],
    "method": [
        r"\b\d+\.?\s+(method|approach|framework|model|proposed method)\b",
        r"\b(our method|methodology|approach|framework overview)\b",
    ],
    "experiments": [
        r"\b\d+\.?\s+experiments?\b",
        r"\b\d+\.?\s+experimental results?\b",
        r"\b\d+\.?\s+results?\b",
        r"\bimplementation details\b",
    ],
    "conclusion": [
        r"\b\d+\.?\s+conclusion\b",
        r"\b\d+\.?\s+conclusions\b",
    ],
}

ROLE_RULES = [
    ("contribution_summary", ["contribution", "in summary", "our contributions", "we summarize"]),
    ("method_overview", ["we propose", "in this paper", "our framework", "our method"]),
    ("key_insight", ["we observe", "this observation", "motivates", "insight"]),
    ("limitation", ["however", "nevertheless", "still", "limited", "challenge", "struggle"]),
    ("problem_statement", ["important", "crucial", "task", "problem", "goal"]),
    ("background", []),
]

TEMPLATE_BUCKETS = {
    "problem_expression": [r"\ba key challenge\b", r"\bremains difficult\b", r"\bcritical\b", r"\bcrucial\b"],
    "limitation_expression": [r"\bhowever\b", r"\bcurrent (methods|approaches)\b", r"\bstill\b", r"\blimited\b"],
    "insight_expression": [r"\bwe observe that\b", r"\bthis observation\b", r"\bmotivates\b"],
    "method_expression": [r"\bwe propose\b", r"\bto address this\b", r"\bour method\b", r"\bour framework\b"],
    "experiment_expression": [r"\bextensive experiments\b", r"\bas shown in\b", r"\boutperform\b", r"\bdemonstrate\b"],
    "contribution_expression": [r"\bour contributions\b", r"\bwe make the following contributions\b"],
}


@dataclass
class ExtractionResult:
    text: str
    page_count: int


def clean_string(value: str) -> str:
    return value.encode("utf-8", "replace").decode("utf-8")


def sanitize_json_value(value):
    if isinstance(value, str):
        return clean_string(value)
    if isinstance(value, list):
        return [sanitize_json_value(item) for item in value]
    if isinstance(value, dict):
        return {clean_string(str(key)): sanitize_json_value(item) for key, item in value.items()}
    return value


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pdf-dir", required=True, help="Directory containing PDF files")
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory where per-paper JSON files will be written",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Optional max number of PDFs to process",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing JSON files",
    )
    parser.add_argument(
        "--failures",
        default="",
        help="Optional path to write failure report JSON",
    )
    return parser.parse_args()


def iter_pdfs(pdf_dir: Path) -> Iterable[Path]:
    return sorted(path for path in pdf_dir.glob("*.pdf") if path.is_file())


def sha1_for_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def safe_slug(text: str) -> str:
    value = text.lower()
    value = value.replace("：", " ").replace(":", " ")
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "paper"


def extract_text(pdf_path: Path) -> ExtractionResult:
    reader = PdfReader(str(pdf_path))
    pages = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    text = "\n\n".join(pages)
    return ExtractionResult(text=normalize_text(text), page_count=len(reader.pages))


def normalize_text(text: str) -> str:
    text = clean_string(text)
    text = text.replace("\u00a0", " ")
    text = text.replace("\r", "\n")
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()


def infer_title(text: str, fallback: str) -> str:
    """Prefer the filename-derived title because CVPR filenames are reliable."""
    clean = clean_string(fallback).replace("：", ":").replace("_", " ").strip()
    clean = re.sub(r"\s+", " ", clean)
    return clean


def sentence_split(text: str) -> list[str]:
    compact = re.sub(r"\s+", " ", text).strip()
    if not compact:
        return []
    parts = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9(])", compact)
    return [part.strip() for part in parts if len(part.strip()) > 20]


def find_pattern_positions(text: str, patterns: list[str]) -> list[tuple[int, int]]:
    hits = []
    for pattern in patterns:
        for match in re.finditer(pattern, text, flags=re.IGNORECASE | re.MULTILINE):
            hits.append((match.start(), match.end()))
    return sorted(hits)


def find_numbered_headings(text: str) -> list[tuple[int, int, str]]:
    pattern = re.compile(
        r"(?m)^(?P<label>\d+(?:\.\d+)*\.?)\s+(?P<title>[A-Z][^\n]{1,100})$"
    )
    headings = []
    for match in pattern.finditer(text):
        title = match.group("title").strip()
        if title.startswith("Figure ") or title.startswith("Table "):
            continue
        if len(title.split()) > 18:
            continue
        headings.append((match.start(), match.end(), f"{match.group('label')} {title}"))
    return headings


def slice_from_heading(text: str, target_keywords: list[str]) -> str:
    headings = find_numbered_headings(text)
    target_index = None
    for index, (_, _, heading) in enumerate(headings):
        lower = heading.lower()
        if any(keyword in lower for keyword in target_keywords):
            target_index = index
            break
    if target_index is None:
        return ""
    start = headings[target_index][0]
    if target_index + 1 < len(headings):
        end = headings[target_index + 1][0]
    else:
        end = len(text)
    return text[start:end].strip()


def slice_section(text: str, start_patterns: list[str], end_patterns: list[str]) -> str:
    starts = find_pattern_positions(text, start_patterns)
    if not starts:
        return ""
    start = starts[0][0]
    end = len(text)
    ends = find_pattern_positions(text[start + 1 :], end_patterns)
    if ends:
        end = start + 1 + ends[0][0]
    section = text[start:end]
    return section.strip()


def collect_sections(text: str) -> dict[str, str]:
    abstract = slice_section(
        text,
        [r"(?m)^abstract\b"],
        [r"(?m)^\d+\.?\s+introduction\b", r"(?m)^introduction\b"],
    )
    introduction = slice_from_heading(text, ["introduction"])
    method = slice_from_heading(text, ["method", "approach", "framework", "methodology"])
    experiments = slice_from_heading(text, ["experiment", "experimental results", "results"])
    conclusion = slice_from_heading(text, ["conclusion"])
    return {
        "abstract": abstract,
        "introduction": introduction,
        "method": method,
        "experiments": experiments,
        "conclusion": conclusion,
    }


def chunk_paragraphs(text: str, sentences_per_chunk: int = 4) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", text) if chunk.strip()]
    if len(chunks) >= 2:
        return chunks
    sentences = sentence_split(text)
    grouped = []
    for index in range(0, len(sentences), sentences_per_chunk):
        grouped.append(" ".join(sentences[index : index + sentences_per_chunk]))
    return [chunk for chunk in grouped if chunk]


def infer_role(paragraph: str) -> str:
    lower = paragraph.lower()
    for role, keywords in ROLE_RULES:
        if any(keyword in lower for keyword in keywords):
            return role
    return "background"


def summarize_message(paragraph: str) -> str:
    sentences = sentence_split(paragraph)
    return sentences[0] if sentences else paragraph[:240]


def infer_strategy(paragraph: str, role: str) -> str:
    lower = paragraph.lower()
    if role == "limitation":
        return "Contrasts prior work and emphasizes unresolved weaknesses."
    if role == "key_insight":
        return "Introduces an observation that motivates the proposed direction."
    if role == "method_overview":
        return "Transitions from problem framing to the high-level solution."
    if role == "contribution_summary":
        return "Enumerates takeaways to make the paper's value explicit."
    if "for example" in lower or "such as" in lower:
        return "Uses concrete examples to ground the narrative."
    return "Builds context and advances the paper's argument."


def intro_structure(introduction: str) -> list[dict]:
    items = []
    for index, paragraph in enumerate(chunk_paragraphs(introduction), start=1):
        role = infer_role(paragraph)
        items.append(
            {
                "paragraph_index": index,
                "paragraph_role": role,
                "main_message": summarize_message(paragraph),
                "writing_strategy": infer_strategy(paragraph, role),
                "evidence_text": paragraph[:1200],
            }
        )
    return items


def extract_headings(section_text: str) -> list[str]:
    raw = find_numbered_headings(section_text)
    headings = [heading for _, _, heading in raw]
    deduped = []
    seen = set()
    for heading in headings:
        key = heading.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(heading)
    return deduped


def build_structure(section_text: str, kind: str) -> list[dict]:
    headings = extract_headings(section_text)
    if not headings:
        return []
    results = []
    for heading in headings:
        lower = heading.lower()
        if kind == "method":
            purpose = "Introduces part of the proposed approach."
            if "overview" in lower or "framework" in lower:
                purpose = "Gives the high-level system view before module details."
            elif "training" in lower or "objective" in lower or "loss" in lower:
                purpose = "Defines optimization targets or learning objectives."
            elif "formulation" in lower:
                purpose = "Formalizes the problem and notation."
            strategy = "Presents the method incrementally from overview to components."
        else:
            purpose = "Presents experimental evidence supporting the paper."
            if "implementation" in lower or "setup" in lower:
                purpose = "Defines experimental settings and reproducibility details."
            elif "ablation" in lower:
                purpose = "Tests which design choices matter."
            elif "qualitative" in lower:
                purpose = "Adds visual or case-based evidence."
            strategy = "Uses staged evidence from setup to comparison and analysis."
        results.append(
            {
                "section_heading": heading,
                "purpose": purpose,
                "author_introduction_strategy": strategy,
                "useful_expressions": [],
            }
        )
    return results


def collect_templates(text: str) -> dict[str, list[str]]:
    sentences = sentence_split(text)
    results = {bucket: [] for bucket in TEMPLATE_BUCKETS}
    for sentence in sentences:
        lower = sentence.lower()
        for bucket, patterns in TEMPLATE_BUCKETS.items():
            if any(re.search(pattern, lower, flags=re.IGNORECASE) for pattern in patterns):
                if sentence not in results[bucket]:
                    results[bucket].append(sentence)
    for bucket in results:
        results[bucket] = results[bucket][:12]
    return results


def best_story_sentences(abstract: str, introduction: str, conclusion: str) -> dict[str, str]:
    abstract_sentences = sentence_split(abstract)
    intro_sentences = sentence_split(introduction)
    conclusion_sentences = sentence_split(conclusion)

    def pick(sentences: list[str], keywords: list[str]) -> str:
        for sentence in sentences:
            lower = sentence.lower()
            if any(keyword in lower for keyword in keywords):
                return sentence
        return sentences[0] if sentences else ""

    return {
        "problem": pick(intro_sentences or abstract_sentences, ["challenge", "problem", "difficult", "crucial"]),
        "limitation": pick(intro_sentences or abstract_sentences, ["however", "limited", "struggle", "fail"]),
        "insight": pick(abstract_sentences + intro_sentences, ["observe", "motivate", "insight"]),
        "proposed_method": pick(abstract_sentences + intro_sentences, ["we propose", "our method", "we introduce"]),
        "experimental_evidence": pick(abstract_sentences + conclusion_sentences, ["experiment", "demonstrate", "outperform", "show"]),
    }


def build_core_story(story_sentences: dict[str, str]) -> dict[str, str]:
    summary_parts = [story_sentences[key] for key in ["problem", "limitation", "insight", "proposed_method", "experimental_evidence"] if story_sentences[key]]
    return {
        **story_sentences,
        "summary": " ".join(summary_parts[:5]),
    }


def notable_sentences(text: str) -> list[str]:
    sentences = sentence_split(text)
    ranked = []
    preferred_terms = [
        "however",
        "we observe",
        "we propose",
        "extensive experiments",
        "our contributions",
        "as shown in",
    ]
    for sentence in sentences:
        score = sum(term in sentence.lower() for term in preferred_terms)
        if len(sentence) > 240:
            score -= 1
        ranked.append((score, sentence))
    ranked.sort(key=lambda item: (-item[0], item[1]))
    unique = []
    seen = set()
    for _, sentence in ranked:
        if sentence not in seen:
            seen.add(sentence)
            unique.append(sentence)
        if len(unique) >= 12:
            break
    return unique


def analyze_pdf(pdf_path: Path) -> dict:
    source_sha1 = sha1_for_file(pdf_path)
    extraction = extract_text(pdf_path)
    title = infer_title(extraction.text, pdf_path.stem)
    paper_id = f"{safe_slug(title)[:80]}--{source_sha1[:10]}"
    sections = collect_sections(extraction.text)
    story_sentences = best_story_sentences(
        sections["abstract"],
        sections["introduction"],
        sections["conclusion"],
    )
    combined_text = "\n\n".join(
        section for section in [
            sections["abstract"],
            sections["introduction"],
            sections["method"],
            sections["experiments"],
            sections["conclusion"],
        ]
        if section
    )
    return {
        "paper_id": paper_id,
        "paper_title": clean_string(title),
        "analysis_version": "v1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "pdf_path": clean_string(str(pdf_path)),
            "filename": clean_string(pdf_path.name),
            "sha1": source_sha1,
            "page_count": extraction.page_count,
        },
        "core_story": build_core_story(story_sentences),
        "introduction_structure": intro_structure(sections["introduction"]),
        "method_structure": build_structure(sections["method"], kind="method"),
        "experiment_structure": build_structure(sections["experiments"], kind="experiments"),
        "writing_templates": collect_templates(combined_text),
        "notable_sentences": notable_sentences(combined_text),
        "raw_sections": sections,
    }


def main() -> int:
    args = parse_args()
    pdf_dir = Path(args.pdf_dir).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    failures = []
    pdfs = list(iter_pdfs(pdf_dir))
    if args.limit > 0:
        pdfs = pdfs[: args.limit]

    for index, pdf_path in enumerate(pdfs, start=1):
        try:
            analysis = sanitize_json_value(analyze_pdf(pdf_path))
            output_path = output_dir / f"{analysis['paper_id']}.json"
            if output_path.exists() and not args.overwrite:
                continue
            with output_path.open("w", encoding="utf-8") as handle:
                json.dump(analysis, handle, ensure_ascii=False, indent=2)
            print(clean_string(f"[{index}/{len(pdfs)}] wrote {output_path.name}"))
        except Exception as exc:  # noqa: BLE001
            failures.append(
                {
                    "pdf_path": clean_string(str(pdf_path)),
                    "error": clean_string(str(exc)),
                }
            )
            print(
                clean_string(f"[{index}/{len(pdfs)}] failed {pdf_path.name}: {exc}"),
                file=sys.stderr,
            )

    if args.failures:
        failure_path = Path(args.failures).expanduser().resolve()
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        with failure_path.open("w", encoding="utf-8") as handle:
            json.dump(
                {
                    "generated_at": datetime.now(timezone.utc).isoformat(),
                    "failure_count": len(failures),
                    "failures": failures,
                },
                handle,
                ensure_ascii=False,
                indent=2,
            )

    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
