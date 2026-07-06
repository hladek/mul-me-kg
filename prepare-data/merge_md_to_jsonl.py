#!/usr/bin/env python3
"""Merge Slovak and English markdown files into a single JSONL file.

For each pair of files matching by prefix before _sk.md / _en.md,
writes one JSONL line with name, sk, and en fields.
"""

import json
import sys
from pathlib import Path


def merge(root: str, output: str) -> None:
    base = Path(root)
    sk_dir = base / "sk"
    en_dir = base / "en"

    # Build lookup: prefix -> sk_content / en_content
    sk_files = {p.name.removesuffix("_sk.md"): p.read_text(encoding="utf-8") for p in sk_dir.glob("*_sk.md")}
    en_files = {p.name.removesuffix("_en.md"): p.read_text(encoding="utf-8") for p in en_dir.glob("*_en.md")}

    # Use sk prefixes as the primary key (sk dir is the larger set)
    matched = 0
    missing_en = 0
    skipped_short = 0
    with open(output, "w", encoding="utf-8") as fout:
        for prefix in sorted(sk_files):
            content_sk = sk_files[prefix]
            content_en = en_files.get(prefix)
            if content_en is None:
                missing_en += 1
                continue
            if len(content_sk) < 1000 or len(content_en) < 1000:
                skipped_short += 1
                continue
            matched += 1
            name = prefix.split("-", 1)[0]
            record = {"name": name, "sk": content_sk, "en": content_en}
            fout.write(json.dumps(record, ensure_ascii=False) + "\n")

    print(f"Matched: {matched}, Missing EN: {missing_en}, Short: {skipped_short}, Total SK: {len(sk_files)}")


if __name__ == "__main__":
    root = "/mnt/sharedhome/hladek/corpora/pil_spc"
    output = sys.argv[1] if len(sys.argv) > 1 else f"{root}/pil_spc.jsonl"
    merge(root, output)
