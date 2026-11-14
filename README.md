# Ideas for a Paper on Multilingual Knowledge Graphs

## Problem Statement

Retrieval-augmented generation (RAG) systems can use knowledge graphs to improve both their performance and explainability. Structured knowledge about named entities and the relationships between them enables more accurate retrieval, provides transparent reasoning paths, and increases the overall usefulness of these systems. These capabilities are particularly important in high-stakes domains such as medicine and law, where explainability and factual accuracy are essential.

However, most existing knowledge graphs are closely tied to a single language, predominantly English. Automatically constructing knowledge graphs for multilingual settings remains challenging, particularly when one or more of the target languages are low-resource languages. Although multilingual large language models have shown promising capabilities, generating high-quality multilingual knowledge graphs remains an open research problem.

As a result, medical question-answering and retrieval systems for lower-resourced languages often rely on English knowledge graphs or require the costly manual or automatic construction of language-specific alternatives. This dependency limits both the quality and accessibility of knowledge-intensive AI applications across languages.

Advancing multilingual GraphRAG systems therefore requires new methods for multilingual and cross-lingual knowledge graph construction, alignment, and representation. Developing language-agnostic knowledge representations that preserve semantic fidelity while remaining interpretable and explainable is a key research direction for enabling robust and trustworthy retrieval-augmented generation across diverse languages.

## Experiment Plan

We could automatically create knowledge graphs for multiple languages and compare the results across languages and, where possible, against existing knowledge graphs, such as **MedDRA**.

1. Create an evaluation scenario that includes multiple languages, with questions, expected relevant documents, and expected answers.
2. Analyze the automatically created knowledge graphs, compare them with one another and, where possible, with existing knowledge graphs. Evaluate both the quality of the knowledge graphs and the retrieval performance.
3. Propose a method to improve multilingual knowledge graph creation and its use in retrieval.
4. Evaluate the research hypotheses through experiments.
5. Summarize the results and finalize the paper.

## Possible Research Questions

* **RQ1:** How can multilingual LLMs automatically extract entities and relationships from multilingual medical texts?
* **RQ2:** How can the extracted knowledge be aligned into a language-agnostic knowledge graph?
* **RQ3:** How does the use of multilingual knowledge graphs affect retrieval quality and answer generation in GraphRAG?
* **RQ4:** How does multilingual GraphRAG compare with English-centric GraphRAG in terms of accuracy, explainability, and user trust for low-resource languages?

## Open Tasks

* Add your language to the parallel corpus
* Propose method for triplet extraction
* Create/update code and prompts for triplet creation and automatically extract triplets.
* Create parallel medical QA evaluation corpus - Create example medical questions and answers for your language
* Evaluate and correct extacted knowledge triplets
* Manually create some knowledge triplets.
* Propose graph RAG method for Medical QA.
* Evaluate medical QA 

## How You Can Help

* Join the initiative.
* Provide feedback on the experiment plan and research questions.
* Help select an existing evaluation dataset or create a new one.
* Contribute to any stage of the experiment plan, experiments, or paper writing.

## Resources

### Data

* Parallel corpus of extracted text from English and Slovak EMA package inserts: https://huggingface.co/datasets/multilingual-medical-kg/pil-spc
* Can be extended to include additional EMA languages.

## Relevant Tools

* https://github.com/pykeen/pykeen — Graph embeddings and datasets
* https://github.com/hkuds/minirag — GraphRAG system
* https://lightrag.github.io/ — GraphRAG system
* https://cogdb.io/ — Embedded Python graph database
* https://neo4j.com/ — Graph database
* https://networkx.org/documentation/stable/index.html — Graph analysis library
* https://gephi.org/ — Graph visualization for GraphML

## Relevant Papers

## RAG Evaluation

- [PILs of Knowledge](https://dl.acm.org/doi/abs/10.1145/3726302.3730283) — Synthetic benchmark for evaluating QA systems on pharmaceutical Patient Information Leaflets using LLM-generated questions and answers.
- [OAGLLM](https://link.springer.com/chapter/10.1007/978-981-96-3752-2_16) — Retrieval-augmented LLM for answering questions about medication instructions from structured drug labels.
- [FDARxBench](https://arxiv.org/abs/2603.19539) — Expert-curated benchmark for evaluating AI on FDA drug labeling questions, covering factual retrieval, multi-step reasoning, and safe refusal.
- [Pharmaceutical Chatbot KG](https://link.springer.com/article/10.1007/s42044-026-00396-3) — A chatbot system combining generative AI with knowledge graphs for pharmaceutical information retrieval.
- [PharmaQA.IT](https://aclanthology.org/2026.eacl-industry.70/) — Expert-validated Italian QA dataset (861 entries) derived from national regulatory drug leaflets.
- [OnSIDES](https://www.medrxiv.org/content/10.1101/2024.03.22.24304724v1) — Machine-readable adverse drug event database extracted from FDA Structured Product Labels using PubMedBERT.

## Knowledge Graph Construction

- [Personalized Knowledge Graphs for the Pharmaceutical Domain](https://link.springer.com/chapter/10.1007/978-3-030-30796-7_25) — Approaches to building individualized knowledge graphs in the pharmaceutical domain.
- [SIDEKICK](https://link.springer.com/chapter/10.1007/978-3-032-25159-6_14) — A semantically integrated resource for drug effects, indications, and contraindications.
- [MEDAKA](https://arxiv.org/abs/2509.26128) — An end-to-end pipeline that constructs biomedical knowledge graphs from unstructured drug leaflets using web scrapers and LLMs, capturing side effects, contraindications, and dosage guidelines.
- [ODAE](https://link.springer.com/article/10.1186/s12859-019-2729-1) — An ontology-based framework for systematic representation of drug adverse events, mapping side effects across varying patient demographics and medical conditions.
- [IEEE](https://ieeexplore.ieee.org/abstract/document/11216837?casa_token=PL5OItOBZAgAAAAA:Lm9AN76bhCDRbj0lmRcQwaIkYHNPfQdQ3xcLgqyF4E6YpbOD8EJ7Nq4l7BrSLbKN7Dm-ua9HpIYR) — Knowledge graph construction method.
- [PharmGraph-Auditor](https://arxiv.org/abs/2603.10891) — A hybrid knowledge-grounded framework for safe prescription verification, combining iterative schema refinement with chain-of-verification reasoning over a unified graph and relational knowledge base.


## Parse package inserts into sections

`parse_package_inserts.py` splits the Slovak (`sk`) and English (`en`) texts into
standard numbered SmPC sections (including subsections such as `4.1`), packaging
label sections, and patient leaflet sections. It uses local rules, without an LLM
or API credentials. The text parser itself uses only the Python standard library;
loading Hugging Face or Arrow data additionally requires `datasets` from
`requirements.txt`.

Process a Hugging Face split (`train`, `test`, or `validation`):

```bash
.venv/bin/python parse_package_inserts.py \
  --split train \
  --output output/sections/pil_spc_train.sections.jsonl \
  --report output/sections/train-report.json
```

Or process a local bilingual JSONL file (one object with `name`, `sk`, and `en`
per line). Cached Hugging Face `.arrow` files are also accepted:

```bash
.venv/bin/python parse_package_inserts.py \
  --input prepare-data/pil_spc_train.jsonl \
  --output output/sections/pil_spc_train.sections.jsonl \
  --report output/sections/train-report.json
```

Add `--limit 10` for a small sample. The remote dataset names its development
split `validation`; the older local `prepare-data/split_data.py` names it `dev`.
Pass that local file explicitly with `--input`.

Each output record retains metadata such as `name`. Its `sk` and `en` values
become objects with `language`, `template` (`human` or `veterinary`), `sections`,
and `warnings`. Each section contains:

- `kind`: `smpc`, `labelling`, `pil`, `annex_ii`, `annex_iv`, or `unknown`.
- `document_index`: a one-based index within the kind, retaining repeated
  documents for different strengths or formulations. Indices are local to each
  language, and do not imply that the corresponding documents are aligned.
- `number` and `parent_number`: the source section number and its parent
  (`4.1` belongs to `4`); introductions and annex markers use `null`.
- `title`: the original heading, with surrounding Markdown formatting stripped.
- `start`, `heading_end`, `end`: character offsets into the original language
  string, with exclusive end offsets.
- `text`: the exact original slice, including its heading and source formatting.

The sections partition the source without dropping or duplicating characters:
`''.join(s['text'] for s in parsed['sections']) == original_text`.
Parent sections contain their own text only, followed by separate subsection
spans. Introduction and annex-marker spans retain unnumbered material. Unnumbered
subheadings, tables, pictures, and annex conditions remain inside their containing
span. Markdown and HTML/OCR headings are recognized, including headings joined
onto one line. Leaflet contents lists stay in the introduction rather than
becoming duplicate sections.

Missing standard headings and repeated section numbers produce review warnings.
These are structural checks, not an accuracy score: older leaflet templates,
missing OCR text, unusual headings, and extraction duplicates need review.
Unrecognized text is preserved in the containing span. Human inserts use the standard EMA heading
titles. Veterinary inserts are detected separately and also use layout and
capitalization rules to support their different section numbering, including
`4.10`, `4.11`, and longer leaflets. For veterinary inserts, missing-section
checks cover gaps in the observed main-section numbering; human inserts are
checked against the standard template. Neither mode infers or translates missing
content, or aligns sections across languages. Existing graph extraction inputs
are unchanged; this output has a different schema.

The parser can also be imported:

```python
from parse_package_inserts import parse_insert, parse_record

parsed = parse_insert(slovak_text, "sk")
leaflet_sections = [s for s in parsed["sections"]
                    if s["kind"] == "pil" and s["number"]]
bilingual = parse_record({"name": "example", "sk": slovak_text, "en": english_text})
```

Run regression checks with:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

### Dataset inspection (2026-11-13)

The cached dataset contains 1,834 bilingual records: 1,467 train, 183 test, and
184 validation. The source columns are `name`, `sk`, and `en`; neither language
has empty texts. Median source lengths are 94,888 characters in Slovak and
93,233 in English. A single record can contain multiple SmPCs, labels, and
leaflets, and the corpus includes veterinary products as well as human medicines.

There are 91 repeated product-name values, of which 52 occur in more than one
split. Names therefore cannot serve as unique document identifiers. Name overlap
alone does not establish duplicate document content. The parser preserves record
order and repeated names in JSONL.

Parsed versions of all splits are generated locally in `output/sections/`,
with file names `pil_spc_<split>.sections.jsonl`. The same directory contains
`inspection.json` with corpus parsing statistics and warning examples, and
`source-inspection.json` with source lengths and name-overlap details. Generated
files are excluded from Git.

The full corpus run verified exact text reconstruction for all 3,668 language
texts. Twelve regression tests cover inline headings, HTML/OCR text, contents
lists, repeated documents, veterinary numbering, Unicode offsets, references,
and the JSONL command-line interface. Coverage warnings remain in the output
for malformed, incomplete, duplicated, or unrecognized headings; lossless text
preservation does not establish that every semantic section boundary is correct.

## Build a graph from parsed sections

`build_pil_spc_graph.py` now calls `parse_package_inserts.parse_insert` on each
raw language text before extraction. It sends one request per section containing
body text, including introductions, labels, annex material, and unrecognized
spans. Pure headings are skipped. Parser warnings are printed for review.
No separate parser command is required, and the builder continues to read raw
`sk`/`en` strings rather than the parser's standalone output schema.

```bash
.venv/bin/python build_pil_spc_graph.py --language sk --split train --limit 1
.venv/bin/python build_pil_spc_graph.py --language en --split validation --limit 1
```

For local raw JSONL splits, add `--data-dir /path/to/splits`. The existing API
settings (`AUTH_TOKEN`/`OPENAI_API_KEY`, `BASE_URL`/`OPENAI_BASE_URL`, and
`MODEL_NAME` or `--model`) still apply. Each section is an independent model
request, so a document can require many requests; `--limit` counts records.

The extraction prompt accepts `[]` for sections with no extractable facts.
Each validated section is appended immediately to the record’s JSONL file,
so extracted knowledge remains available if a later section fails. Exact
assertions already saved in that file are not appended again. After every
section response validates, the saved triples are imported into CogDB. Each triple receives authoritative
`source_document` and `source_section` values from the builder. A section ID such
as `smpc:1:4.2@1234` identifies the document kind, repeated-document index, section
number, and starting character offset. Dose, contraindication, and interaction
node IDs receive a deterministic section suffix so sequences restarted in
separate model calls cannot merge unrelated facts.

Output files are named `<normalized-name>-<source-text-hash>.jsonl`, retaining
records that share a product name. When a record has no explicit identifier,
its document identifier also includes that hash. Older name-only output files
are not used as completion markers. Completed hashed outputs are skipped unless
`--overwrite` is supplied. Reprocessing appends newly extracted assertions and
preserves saved knowledge. A `.jsonl.incomplete` sidecar marks a record while it
is being processed and is removed after graph import succeeds. On failure, the
partial JSONL and sidecar remain; retrying processes the sections again and
deduplicates saved assertions before appending. Graph writes add
assertions and do not remove previously imported facts.

The integration tests mock the model and graph storage, checking section isolation,
Slovak/English extraction, provenance, fact-node separation, empty results,
duplicate product names, resume behavior, and failure handling without API calls.
