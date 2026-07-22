# Ideas for a paper in Multilingual Knowledge Graphs

## Problem Statement

Retrieval-augmented generation (RAG) systems can use knowledge graphs to improve both their performance and explainability. Structured knowledge about named entities and the relationships between them enables more accurate retrieval, provides transparent reasoning paths, and increases the overall usefulness of these systems. These capabilities are important in high-stakes domains such as medicine and law, where explainability and factual accuracy are essential.

However, most existing knowledge graphs are closely tied to a single language, predominantly English. Automatically constructing knowledge graphs for multilingual settings remains challenging, particularly when one or more of the target languages are low-resource languages. Although multilingual large language models have shown promising capabilities, generating high-quality multilingual knowledge graphs remains an open research problem.

As a result, medical question-answering and retrieval systems for lower-resourced languages often rely on English knowledge graphs or require the costly manual or automatic construction of language-specific alternatives. This dependency limits both the quality and accessibility of knowledge-intensive AI applications across languages.

Advancing multilingual GraphRAG systems therefore requires new methods for multilingual and cross-lingual knowledge graph construction, alignment, and representation. Developing language-agnostic knowledge representations that preserve semantic fidelity while remaining interpretable and explainable is a key research direction for enabling robust and trustworthy retrieval-augmented generation across diverse languages.

## Experiment Plan

We could automatically create a knowledge graph for multiple languages and compare the results among them and possibly with existing knowledge graphs, such as [Meddra]([https://www.meddra.org/).

1. Index existing multilingual data (drug packege inserts) using a GraphRAG techique.
2. Create an evaluation scenario that includes multiple languages - questions, expected relevant documents and expected answers.
3. Observe the automatically created knowledge graphs, compare them among themselves and possibly with existing knowledge graphs. Evaluate the knowledge graphs and retrieval.
4. Propose a a way to improve multilingual KG creation and exploitation in retrieval.
5. Evaluate the research hypotheses in experiments.
6. Summarize the results and finalize the paper.

## Possible research questions

- RQ1: How can multilingual LLMs automatically extract entities and relations from multilingual medical texts?
- RQ2: How can extracted knowledge be aligned into a language-agnostic knowledge graph?
- RQ3: How does the use of multilingual knowledge graphs affect retrieval quality and answer generation in GraphRAG?
- RQ4: How does multilingual GraphRAG compare with English-centric GraphRAG in terms of accuracy, explainability, and user trust for low-resource languages?

## How can you help

- Join the initiative.
- Comment on Experiment Plan and Research Questions.
- Help to pick exxisting or create a new evaluation dataset.
- Help with any step of Experiment Plam, Experiments and Paper. 

## Resources

Data:

- Parallel corpus of extracted text from English and Slovak package inserts from EMA [multilingual-medical-kg/pil-spc](https://huggingface.co/datasets/multilingual-medical-kg/pil-spc)
- Can be extended for other languages of EMA

## Relevant Tools

- https://github.com/pykeen/pykeen - Graph Embeddings and Datasets
- https://github.com/hkuds/minirag - GraphRAG system
- https://lightrag.github.io/ - GraphRAG system
- https://cogdb.io/ - embedded Python graph database
- https://neo4j.com/ - graph database
- https://networkx.org/documentation/stable/index.html
- https://gephi.org/ - graph visualization for GraphML
