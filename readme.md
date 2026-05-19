#  LangGraph Summarization Agent  

Overview:

* Extracts structured content from website (https://www.geeksforgeeks.org/) (via Playwright)
* Cleans and normalizes the data
* Generates  summaries using an LLM
* Optionally evaluates output quality using DeepEval
* Tracks everything using Langfuse observability
* Exposes the pipeline via FastAPI APIs

---

## Architecture Overview

```
Playwright (API Capture)
        ↓
Normalization (HTML Cleaning)
        ↓
Prompt Engineering
        ↓
LLM (OpenRouter)
        ↓
Evaluation (DeepEval)
        ↓
Observability (Langfuse)
        ↓
FastAPI Endpoints
```

---

## Tech Stack

* **Web Scraping**: Playwright (async)
* **LLM**: OpenRouter (`gpt-4o-mini`)
* **Orchestration**: LangGraph
* **Evaluation**: DeepEval(Hallucination,Faithfulness,AnswerRelevancy) -> llm (Openrouter)
* **Observability**: Langfuse
* **Backend API**: FastAPI



---

##  Environment Variables

Create a `.env` file in the root:

```env
# LLM
OPENROUTER_API_KEY=your_openrouter_key



# Login credentials (Geeks for Geeks login cred)
LOGIN_EMAIL=your_email
LOGIN_PASSWORD=your_password

# Langfuse cred
LANGFUSE_PUBLIC_KEY=your_key
LANGFUSE_SECRET_KEY=your_secret
LANGFUSE_HOST=https://cloud.langfuse.com
```

---

## Running the Application

### Start FastAPI Server

```bash
python server.py
```

Server runs at:

```
http://localhost:8000
```

---

##  API Endpoints

### 1. Health Check

```http
GET /
```

Response:

```json
{
  "Message": "Api is Running"
}
```


---

### 2. Full LLM Pipeline (Summary + Evaluation)

```http
POST /llm_test?url=...&section=...&evaluation=true  

-> section (Python Tutorial,Data Types,Interview Questions) any one of these
url -> https://www.geeksforgeeks.org/
evaluation = true -> uses DeepEval for Evaluation
evaluation = false -> skips the deepeval

```

#### Response:

```json
{
  "section": "Software Engineering Tutorial",
  "summary": "...",
  "eval_score": 0.82,
  "eval_pass": true,
  "eval_notes": "Faithfulness: 0.9, Relevancy: 0.85, Hallucination: 0.1",
  "trace_id": "abc123"
}
```

---

## Pipeline Flow (LangGraph)

### Nodes:

1. **extract_node** 
   * Captures API response using Playwright with log in cred and section wise
2. **normalize_node**

   * Cleans HTML and structures content
3. **prompt_node**

   * Generates section-specific prompt
4. **summarization_node**

   * Calls LLM (OpenRouter) for summarization 
5. **evaluation_node (optional)**

   * Runs DeepEval metrics:

     * Faithfulness
     * Relevancy
     * Hallucination

---

## Evaluation Logic

Final score:

```
score = (faithfulness + relevancy + (1 - hallucination)) / 3
```

Pass criteria:

* Faithfulness ≥ 0.7
* Relevancy ≥ 0.7
* Hallucination < 0.3

---

## Important Notes

* Playwright runs in **non-headless mode** (`headless=False`) for debugging.
* Website structure (e.g., GeeksforGeeks) may change → selectors may break.
* API capture depends on `_next/data` pattern (Next.js apps).
* Login cred is required 

---
