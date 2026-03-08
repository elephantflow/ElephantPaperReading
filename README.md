# ElephantPaperReading

Elephant helps your paper reading, but the repository is optimized for one specific asset:

- one paper -> one JSON record
- writing-first analysis rather than method-only summaries
- batch processing of large PDF folders

## Repository Layout

```text
ElephantPaperReading/
  analyses/
    cvpr2025/
      *.json
  schemas/
    paper_analysis.schema.json
  scripts/
    analyze_papers.py
```

## What Each JSON Contains

Each paper record stores:

- source metadata
- core research story
- introduction structure
- method organization
- experiment narrative structure
- reusable writing templates
- notable sentences
- raw extracted sections

The canonical schema is [schemas/paper_analysis.schema.json](/Users/gulucaptain/Documents/Codex/ElephantPaperReading/schemas/paper_analysis.schema.json).

## Batch Run

Example for the CVPR 2025 PDF folder:

```bash
python3 scripts/analyze_papers.py \
  --pdf-dir /Users/gulucaptain/Downloads/cvpr2025 \
  --output-dir analyses/cvpr2025 \
  --failures analyses/cvpr2025/_failures.json \
  --overwrite
```

For a quick smoke test:

```bash
python3 scripts/analyze_papers.py \
  --pdf-dir /Users/gulucaptain/Downloads/cvpr2025 \
  --output-dir analyses/cvpr2025 \
  --failures analyses/cvpr2025/_failures.json \
  --limit 3 \
  --overwrite
```

## Notes

- Extraction currently uses `pypdf`, so image-only PDFs may fail or produce sparse text.
- The analysis is heuristic but deterministic, which makes it suitable for large-scale first-pass indexing.
- Higher-quality narrative interpretation can be layered on top later without breaking the per-paper JSON format.
