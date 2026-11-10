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

