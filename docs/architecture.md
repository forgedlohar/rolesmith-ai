# Architecture

Rolesmith AI is structured with a distinct separation between generic browser automation and intelligent decision-making.

## Core Modules

### `rolesmith_ai.pipeline` (The Brain)
- **`pipeline.py`**: The main orchestration state machine.
- **`llm.py` & `llm_answers.py`**: Interacts with OpenAI/Groq for reasoning, JD rating, and form Q&A generation.
- **`rating.py`**: Rates Job Descriptions against the `CandidateProfile`.
- **`tailor.py`**: Chooses which bullets to include/exclude for a specific application.
- **`render.py`**: Renders the finalized resume using `pdflatex`.
- **`models.py`**: Pydantic schemas validating all data exchanged within the pipeline.

### `rolesmith_ai.tools` (The Muscle)
- **`apply.py`**: Contains the Playwright logic to navigate sites, find inputs, handle iframes, and perform applications.
- **`search.py`**: Browser automation to scrape job listings.
- **`tracker.py`**: Manages the SQLite database tracking application histories to prevent duplicate submissions and rate limits.
- **`session.py`**: Handles persistent cookies and browser profiles.

### `rolesmith_ai.server` (The Interface)
Exposes the underlying logic via FastMCP for Claude Desktop integration. Allows LLM assistants to trigger background tasks and review shortlists.
