#!/usr/bin/env python3
"""Split pil_spc.jsonl into 80/10/10 train/test/dev sets."""

import json
import random
import sys
from pathlib import Path

random.seed(42)

input_path = Path(__file__).parent / "pil_spc.jsonl"
data = [json.loads(line) for line in input_path.read_text(encoding="utf-8").strip().splitlines()]

random.shuffle(data)

n = len(data)
train_end = int(n * 0.8)
test_end = train_end + int(n * 0.1)

splits = {
    "train": data[:train_end],
    "test": data[train_end:test_end],
    "dev": data[test_end:],
}

for name, items in splits.items():
    out = input_path.with_name(f"pil_spc_{name}.jsonl")
    out.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n", encoding="utf-8")
    print(f"{name}: {len(items)} items ({len(items)/n*100:.1f}%)")
