# Controversial Murder Mystery Generator

This project implements a multi-step LLM-based system that generates:

- A controversial victim and theme
- Seven interconnected character sheets (with secrets and hints)
- Short dialogues between the characters
- Character portraits via an AI image generator (tool-based)

It also integrates a basic RAG (Retrieval-Augmented Generation) setup to enrich character backgrounds with external knowledge and to reference sources.

## Project Structure

```text
project/
 ├─ main.py
 ├─ llm_pipeline/
 │   ├─ __init__.py
 │   ├─ case_generator.py
 │   ├─ character_generator.py
 │   ├─ dialogue_generator.py
 ├─ rag/
 │   ├─ __init__.py
 │   ├─ retriever.py
 ├─ image_tool/
 │   ├─ __init__.py
 │   ├─ image_generator.py
 ├─ README.md
 ├─ requirements.txt
