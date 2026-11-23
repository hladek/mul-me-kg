# Ideas for a Paper on Multilingual Knowledge Graphs

## Plan Phase 1 \- How to generate knowledge in a multilingual scenario?

We could automatically create knowledge graphs for multiple languages and compare the results across languages with the same ontology on the parallel corpus.

1. Finish the ontology and rule extraction framework.  
2. Set up manual annotation. Annotate several items in multiple languages.  
3. Do evaluation study \- what is the quality of the automatically generated knowledge in multiple scenarios?

Possible research questions:

- How does the quality of the generated knowledge correlate with the quality of the language model?  
- What are the differences among knowledge graphs in multiple languages?  
- Can knowledge graphs be transferred into different languages by machine translation?

## Plan Phase 2 \- How to utilize knowledge graphs in a cross lingual scenario?

Use the dataset and the knowledge graphs to build and evaluate  cross-lingual / multilingual question answering system:

1. Propose GraphRAG for medical question answering.  
2. Create the evaluation dataset or adjust the existing dataset. Each question will have expected answers, relevant documents and relevant knowledge.  
3. Objectively evaluate the QA system in multiple scenarios.

Possible research questions:

- Can you mix languages in single knowledge graphs? How?  
- Can you use multiple different language knowledge graphs with multilingual data?  
- How can you utilize a knowledge graph in a cross-lingual scenario?

## How You Can Help

* Join the initiative.
* Provide feedback on the experiment plan and research questions.
* Help select an existing evaluation dataset or create a new one.
* Contribute to any stage of the experiment plan, experiments, or paper writing.

## Problem Statement

Retrieval-augmented generation (RAG) systems can use knowledge graphs to improve both their performance and explainability. Structured knowledge about named entities and the relationships between them enables more accurate retrieval, provides transparent reasoning paths, and increases the overall usefulness of these systems. These capabilities are particularly important in high-stakes domains such as medicine and law, where explainability and factual accuracy are essential.

However, most existing knowledge graphs are closely tied to a single language, predominantly English. Automatically constructing knowledge graphs for multilingual settings remains challenging, particularly when one or more of the target languages are low-resource languages. Although multilingual large language models have shown promising capabilities, generating high-quality multilingual knowledge graphs remains an open research problem.

As a result, medical question-answering and retrieval systems for lower-resourced languages often rely on English knowledge graphs or require the costly manual or automatic construction of language-specific alternatives. This dependency limits both the quality and accessibility of knowledge-intensive AI applications across languages.

Advancing multilingual GraphRAG systems therefore requires new methods for multilingual and cross-lingual knowledge graph construction, alignment, and representation. Developing language-agnostic knowledge representations that preserve semantic fidelity while remaining interpretable and explainable is a key research direction for enabling robust and trustworthy retrieval-augmented generation across diverse languages.

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

## Extract information from SmPCs only

`extract_smpc.py` extracts the product identity and clinical statements defined
in `ontology.py` using the OpenAI SDK. It has no CogDB dependency and does not
import the graph builder. Install `openai`, `python-dotenv`, and `datasets`
(the last is needed only for Hugging Face or Arrow input).

Configure `OPENAI_API_KEY` and `MODEL_NAME` in the environment or `.env`.
`AUTH_TOKEN` and `BASE_URL` are also supported for compatibility with existing
configuration; they take precedence over `OPENAI_API_KEY` and
`OPENAI_BASE_URL`, respectively. `--model` overrides `MODEL_NAME`.

Process a small sample from a raw bilingual JSONL file:

```bash
.venv/bin/python extract_smpc.py \
  --input prepare-data/pil_spc_train.jsonl \
  --language sk --split train --limit 1
```

Or load a Hugging Face split:

```bash
.venv/bin/python extract_smpc.py \
  --language en --split validation --limit 1
```

`--data-dir prepare-data --split dev` selects the local
`pil_spc_dev.jsonl` file; remote `dev` selects `validation`.
Inputs contain raw `sk`/`en` text, not the previously generated section objects.
`--limit` counts input records, which may each contain multiple SmPCs.

The new `parse_package_inserts.parse_smpc(text, language)` entry point returns
only SmPC spans with offsets into the original language text. It reuses the
rule-based heading recognizer but skips leaflet and labelling section parsing.
Annex/leaflet/labelling markers terminate SmPC spans; an unmarked leaflet's
section 1 also acts as a boundary. Unknown leading text and other document kinds
are excluded. Inputs without recognizable numbered SmPC sections are skipped
with a warning. Missing or malformed source boundary markers may still require
manual review. Repeated SmPCs are processed separately, and veterinary headings
select extraction guidance by meaning rather than human section numbering.

Prompts live in `prompts/smpc-*.txt`; use `--prompt-dir` to choose another folder
containing the same four filenames. Each section with body text gets a separate
API request. The partial Product response schema is generated from `ontology.py`.
The shared prompt requires source-language values and requests verbatim evidence
when available; facts may be extracted without excerpts.
Additional prompts guide identity, clinical, and other sections. Clinical
coverage includes overdose (4.9), pharmacodynamics (5.1), pharmacokinetics
(5.2), and preclinical safety (5.3), alongside the clinical particulars
described above. The ontology does not cover every SmPC fact: unsupported
information yields an empty result,
and the source section remains in the output. Heading-only sections make no API
call. Empty results do not establish that a clinical phenomenon is absent.

## Manually annotate SmPCs

Launch the local Streamlit interface from the repository root:

```bash
.venv/bin/pip install -r requirements.txt
.venv/bin/streamlit run annotate_smpc.py
```

Choose a dataset split and language, then select a product record and one of its
detected SmPC documents. Product names can repeat; the record index and document
index distinguish those choices. The app shows each original numbered section
and provides forms for the ontology fields associated with that section. Other
sections can be marked reviewed without assigning them to an unrelated field.

Enter evidence as an exact excerpt copied from the section. The app records the
source ID, section metadata, language, and document-relative offsets when the
excerpt is found; repeated matches can be selected by occurrence. An unmatched
excerpt is retained with `is_exact` set to false and null offsets. Section
progress is saved as a resumable draft under `output/manual-annotations/`.
**Export Product JSON** writes a standalone `ontology.Product` JSON file in the
same language/split directory. The interface does not call an LLM or other
extraction API. The first dataset load may download the selected split into the
Hugging Face cache.

After every section, the pipeline validates response types, checks each evidence
excerpt against the exact section text, and assigns source IDs in Python.
Matching excerpts have `is_exact=true` and document-relative character offsets.
Supplied unmatched excerpts retain their text with `is_exact=false` and null
offsets. Missing, null, or blank excerpts are discarded; evidence lists with no
remaining excerpts become null. Facts and identity values without evidence are
retained. Available evidence is preserved when duplicate facts are merged.
An exact match verifies source location, not whether an excerpt semantically
supports every extracted attribute. For repeated identical excerpts,
offsets identify the first match within the section.

Local normalization applies Unicode NFC and whitespace cleanup to extracted
values while preserving exact evidence text. It removes identical entries and
combines evidence for otherwise identical statements, including nested
populations. After each document, it repeats normalization across sections.
It preserves case, synonyms, languages, doses, units, conditions, and differing
clinical statements; it performs no translation, synonym linking, or external
terminology lookup. Each section's normalized information is printed to stdout.

By default, files are written to `output/smpc/<language>/<split>/`. There is one
UTF-8 `.json` file per SmPC, with a name derived from the record name, record
identity/content hash, and SmPC index. Use `--output-dir` to change the root.
Each file contains:

- `metadata`: record identity, language, input source, source hash, SmPC index,
  and offsets into the original language text.
- `model`, `prompt_hashes`, and `run_fingerprint`: extraction configuration.
- `template`, `parser_warnings`, and `normalization_warnings`: review context.
- `sections`: original parser spans, status, selected guidance prompt, and
  normalized `information` objects with nullable evidence and matching metadata.
- `product`: aggregated information matching the existing Product fields.
- `identity_conflicts`: differing values for scalar identity fields. Conflicting
  optional fields are left null in the aggregate; all values and evidence remain
  available in section results.

If no unambiguous, source-supported product name is available, `product` is
null and `partial_product` retains the aggregated information. The record name
is never silently substituted for a missing extracted product name.

Successful sections are saved atomically to `.json.incomplete` checkpoints.
Rerunning resumes matching checkpoints and prints their section results again.
Completed documents are skipped. Changed inputs produce distinct identities;
changed prompts, model, implementation, or input-source metadata require
`--overwrite` for an existing output/checkpoint. Overwrite starts that document
again. Failures retain checkpoints, report document/section context, and produce
a nonzero exit status after remaining documents are attempted. No graph database
is created or updated.
