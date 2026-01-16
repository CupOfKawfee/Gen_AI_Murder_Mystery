# Gen_AI_Murder_Mystery

A multi-stage Generative AI project that creates complete, coherent murder mystery scenarios using large language models (LLMs). The system generates a case description, interconnected characters with secrets, clues, a timeline and a final solution. In addition, a lightweight Retrieval-Augmented Generation (RAG) component integrates location-specific dinner menus based on local recipe data.

---

## Problem Statement

Large Language Models are highly capable of generating creative text, but complex narrative scenarios require structured orchestration to ensure consistency, logical coherence, and completeness. This project investigates how a multi-stage LLM pipeline can be designed to generate a full murder mystery scenario, while also integrating external, domain-specific knowledge through a minimal RAG approach.

The primary objective is to demonstrate prompt orchestration, modular system design, and qualitative evaluation of generative outputs.

Out of scope are real-time web search, model fine-tuning, and persistent vector databases.

---

## Features

- Case generator (victim, setting, controversy)
- 7 interconnected characters with individual secrets and motivations
- Timeline of the final day, structured clues, and final resolution
- Optional: character image generation
- RAG component for location-based dinner menus
- Command Line Interface (CLI)
- Web UI via Flask (optional)

---

## Recommended Use
We recommend using Docker to build the application by running:
- open Docker Client
- ```docker build -t gen-ai-murder-mystery ```
- ```docker run -p 5001:5000 –env-file .env.docker gen-ai-murder-mystery```
- have Automatic 1111 up and running with the models mentioned in requirements.
- then, run on: http://localhost:5001/
Make sure you have LMStudio running with the model ”qwen/qwen3-vl-4b”, which we always
used for our generation.

---

## System Architecture

User Input (Location)
↓
Recipe Retrieval (CSV-based RAG)
↓
Case Generation (LLM)
↓
Character Generation (LLM)
↓
Timeline & Clue Generation (LLM)
↓
Final Solution Synthesis
↓
Optional Image Generation

---

## Project Structure

```text
.
├─ main.py                  # CLI entry point
├─ app.py                   # Flask web application
├─ llm_pipeline/            # Prompt orchestration and LLM logic
├─ rag/                     # RAG stub and retrieval logic
├─ recipes/                 # CSV recipe data for menus
├─ image_tool/              # Image generation logic and output
├─ templates/               # HTML templates for Flask UI
├─ requirements.txt
└─ README.md
```

---

## Requirements

- Python 3.10+ (recommended)
- An OpenAI-compatible endpoint (e.g. LM Studio)
- Automatic 1111 with the ADetailer extension:
  - For Image generation: RunDiffusion/Juggernaut-XL-v9 (https://huggingface.co/RunDiffusion/Juggernaut-XL-v9)
  - The Lora model: SDXL-LoRA-slider.nice-hands (https://huggingface.co/ntc-ai/SDXL-LoRA-slider.nice-hands)
- **Flask** for the web UI
- **Flask-Session** for server-side session storage
- **fpdf2** for PDF generation
# Create session storage directory
  mkdir flask_session

- Note: The flask_session/ directory is required for server-side session storage. Session data is stored here instead of browser cookies to handle large mystery data (exceeds 4KB cookie limit).
---

## Installation

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install flask #for web UI
Flask-Session==0.8.0 # stores session data
fpdf2==2.8.5 # for pdf 
cachelib

```

---

## Configuration

The `.env` file controls the LLM endpoint:

```env
LM_STUDIO_BASE_URL=http://localhost:1234/v1
LM_STUDIO_API_KEY=lm-studio
LM_STUDIO_MODEL=Your-Model-Name-Here
```

---

***

## Session Storage

This application uses **Flask-Session** for server-side session storage. Mystery data (typically 7KB+) exceeds the browser cookie limit (4KB), so session data is stored in the `flask_session/` directory on disk.

  **Setup:**
  - The `flask_session/` directory is automatically created or you can create it manually:
    ```bash
    mkdir flask_session

## Usage (CLI)

```bash
python main.py
```

The CLI flow:

1. Prompts the user for a location
2. Retrieves a location-specific dinner menu via RAG
3. Generates the murder mystery scenario
4. Outputs the final case, characters, clues, and solution

## Usage (Web)

```bash
python app.py
```

Then open `http://127.0.0.1:5000` in the browser. Generated character images are stored and served from image_tool/image_output.

---

## Reproducibility

The project was developed and tested with Python 3.11. Due to the probabilistic nature of large language models, generated text outputs are non-deterministic and may vary between runs even with identical inputs.

---

## Design Decisions

- A CSV-based RAG approach was selected to keep the project lightweight, transparent, and fully local without external database dependencies.
- Seven characters were chosen as a balance between narrative complexity and cognitive load for users.
- Prompt-based orchestration was preferred over model fine-tuning to emphasize system design and prompt engineering.

---

## Error Handling and Fallbacks

- If image generation fails or is disabled, a static fallback image is used.
- If no recipes are found for a given location, a generic dinner menu is generated.
- The system is designed to fail gracefully without terminating the full pipeline.

---

## Limitations

- The project relies solely on prompt engineering; no model fine-tuning is applied.
- The RAG component operates on small, structured datasets and does not scale to large corpora.
- Output quality depends strongly on the underlying LLM.