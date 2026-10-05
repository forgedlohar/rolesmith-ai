# Usage Guide

## Quickstart (Standalone)

You can run Rolesmith AI entirely as a standalone Python CLI without Claude Desktop.

1. Install dependencies with `uv sync`.
2. Setup configuration using `uv run python3 -m rolesmith_ai.pipeline setup`.
3. Provide your `resume_template.tex` in `~/.rolesmith_ai/`.
4. Log into target platforms (e.g. LinkedIn) using the browser:
   ```bash
   uv run python3 -m rolesmith_ai.run
   ```
   (Select Option 1 to store interactive sessions).

## The Autopilot Pipeline

The pipeline operates in three distinct phases, which you can run separately or together.

1. **Discover & Rate**: Finds jobs and scores them using the LLM.
   ```bash
   uv run python3 -m rolesmith_ai.pipeline discover --platforms linkedin,wellfound --days 1 --max-rate 20
   ```

2. **Tailor Resumes**: For jobs that pass the minimum score, generates tailored resumes.
   ```bash
   uv run python3 -m rolesmith_ai.pipeline tailor
   ```

3. **Apply**: Uses Playwright to execute applications and answer form questions using the LLM.
   ```bash
   # Dry-run mode (Preview applications without submitting)
   uv run python3 -m rolesmith_ai.pipeline apply

   # Live mode (Actually submit the application)
   uv run python3 -m rolesmith_ai.pipeline apply --live
   ```

## Model Context Protocol (MCP)

To use Rolesmith via Claude Desktop, add it to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "rolesmith": {
      "command": "uv",
      "args": ["run", "rolesmith_ai-server"],
      "env": {
        "OPENAI_API_KEY": "sk-..."
      }
    }
  }
}
```

This exposes tools to Claude like `autopilot_start`, `list_shortlist`, and `review_form_answers`.
