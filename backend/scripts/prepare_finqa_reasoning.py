"""Build a compact, non-customer FinQA reasoning-pattern index.

Only questions and symbolic operation names are retained. Source report values,
answers and tables are deliberately excluded so production responses cannot
mistake dataset facts for a client's business evidence.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import zipfile


TOKEN_RE = re.compile(r"[a-z][a-z0-9_-]+")
OP_RE = re.compile(r"([a-z_]+)\(")


def normalize_question(value: str) -> str:
    return " ".join(TOKEN_RE.findall(value.casefold()))


def build_index(archive: Path, limit: int = 7000) -> dict:
    with zipfile.ZipFile(archive) as source:
        train = json.load(source.open("train.json"))

    operation_counts: Counter[str] = Counter()
    records: list[dict] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for item in train:
        question = normalize_question(item.get("qa", {}).get("question", ""))
        operations = tuple(OP_RE.findall(item.get("qa", {}).get("program", "")))
        if not question or not operations or (question, operations) in seen:
            continue
        seen.add((question, operations))
        operation_counts.update(operations)
        records.append({"question": question, "operations": list(operations)})
        if len(records) >= limit:
            break

    return {
        "model_name": "finqa_symbolic_reasoning_router_v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": {
            "dataset": "FinQA",
            "split": "train",
            "records_seen": len(train),
            "patterns_retained": len(records),
            "license": "CC BY 4.0",
            "url": "https://github.com/czyssrs/FinQA",
        },
        "operation_counts": dict(operation_counts.most_common()),
        "patterns": records,
        "safety": {
            "retained_fields": ["normalized_question", "symbolic_operations"],
            "excluded_fields": ["financial_report", "table", "answer", "numeric_values"],
            "client_data_policy": "routing_only_never_business_evidence",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("archive", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "app" / "data" / "finqa_reasoning_index.json",
    )
    parser.add_argument("--limit", type=int, default=7000)
    args = parser.parse_args()
    artifact = build_index(args.archive, args.limit)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, separators=(",", ":")), encoding="utf-8")
    print(f"Retained {len(artifact['patterns']):,} safe reasoning patterns")
    print(f"Saved {artifact['model_name']} to {args.output}")


if __name__ == "__main__":
    main()
