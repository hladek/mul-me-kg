# Ideas for a Paper on Multilingual Knowledge Graphs

## Problem Statement

Retrieval-augmented generation (RAG) systems can use knowledge graphs to improve both their performance and explainability. Structured knowledge about named entities and the relationships between them enables more accurate retrieval, provides transparent reasoning paths, and increases the overall usefulness of these systems. These capabilities are particularly important in high-stakes domains such as medicine and law, where explainability and factual accuracy are essential.

However, most existing knowledge graphs are closely tied to a single language, predominantly English. Automatically constructing knowledge graphs for multilingual settings remains challenging, particularly when one or more of the target languages are low-resource languages. Although multilingual large language models have shown promising capabilities, generating high-quality multilingual knowledge graphs remains an open research problem.

As a result, medical question-answering and retrieval systems for lower-resourced languages often rely on English knowledge graphs or require the costly manual or automatic construction of language-specific alternatives. This dependency limits both the quality and accessibility of knowledge-intensive AI applications across languages.

Advancing multilingual GraphRAG systems therefore requires new methods for multilingual and cross-lingual knowledge graph construction, alignment, and representation. Developing language-agnostic knowledge representations that preserve semantic fidelity while remaining interpretable and explainable is a key research direction for enabling robust and trustworthy retrieval-augmented generation across diverse languages.

## Experiment Plan

We could automatically create knowledge graphs for multiple languages and compare the results across languages and, where possible, against existing knowledge graphs, such as **MedDRA**.

1. Index existing multilingual data (drug package inserts) using a GraphRAG technique.
2. Create an evaluation scenario that includes multiple languages, with questions, expected relevant documents, and expected answers.
3. Analyze the automatically created knowledge graphs, compare them with one another and, where possible, with existing knowledge graphs. Evaluate both the quality of the knowledge graphs and the retrieval performance.
4. Propose a method to improve multilingual knowledge graph creation and its use in retrieval.
5. Evaluate the research hypotheses through experiments.
6. Summarize the results and finalize the paper.

## Possible Research Questions

* **RQ1:** How can multilingual LLMs automatically extract entities and relationships from multilingual medical texts?
* **RQ2:** How can the extracted knowledge be aligned into a language-agnostic knowledge graph?
* **RQ3:** How does the use of multilingual knowledge graphs affect retrieval quality and answer generation in GraphRAG?
* **RQ4:** How does multilingual GraphRAG compare with English-centric GraphRAG in terms of accuracy, explainability, and user trust for low-resource languages?

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

