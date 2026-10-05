# Antigravity Integration

Rolesmith AI was built from the ground up to operate as a Model Context Protocol (MCP) server. This means you can plug it directly into **Google Antigravity**, allowing the AI agent to completely take over your job search.

When connected to Antigravity, the agent can use Rolesmith's tools to:
- Run searches on your behalf
- Monitor the pipeline status
- Read and tailor your resume for specific jobs
- Bulk apply to jobs while you sleep

---

## 1. Setting up the MCP Server

Antigravity supports connecting to MCP servers via its customization system. You can configure Rolesmith AI either globally or specifically for a single workspace.

### Global Installation (Recommended)
To make Rolesmith AI available to Antigravity no matter what project you are working on, add it to your global MCP configuration:

1. Open or create the global config file: `~/.gemini/config/mcp_config.json`
2. Add the `rolesmith` server:

```json
{
  "mcpServers": {
    "rolesmith": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/rolesmith-ai",
        "run",
        "rolesmith_ai-mcp"
      ],
      "env": {}
    }
  }
}
```
*(Make sure to replace `/absolute/path/to/rolesmith-ai` with the actual path where you cloned this repository).*

### Workspace Installation
If you only want Rolesmith active while you are working in a specific folder, create an `.agents/mcp_config.json` file inside that workspace instead.

---

## 2. Configuring Rolesmith

Before you let Antigravity run the pipeline, make sure you have run the initial interactive login steps, because Antigravity cannot click buttons in your local browser window.

Open a terminal and run:
```bash
# Log in to platforms you want to apply on
uv run rolesmith-ai interactive-login linkedin
uv run rolesmith-ai interactive-login naukri

# Fill out your profile info and passwords
nano ~/.rolesmith/config.json
nano .env
```

---

## 3. Instructing Antigravity

Once the MCP server is connected, Antigravity will automatically load the tools provided by Rolesmith AI (`pipeline_start`, `pipeline_status`, `bulk_apply`, etc.).

You can now use simple natural language prompts to have Antigravity run your job hunt. For example, try telling the Antigravity agent:

> **"Hey, can you start the Rolesmith AI pipeline and do a fresh search for 'Senior Backend Engineer' roles in 'Bangalore' on LinkedIn? Keep checking the status and let me know when it finishes."**

Or, if you want it to run indefinitely:

> **"Use the `/goal` command. Your goal is to run the rolesmith pipeline every 6 hours to search for new Python developer jobs on Naukri and apply to any that get a score over 85."**

### Available MCP Tools for the Agent
Antigravity will have access to the following tools exposed by Rolesmith AI:
- `search_jobs`: Trigger a scraping run on a specific platform.
- `bulk_apply`: Run the end-to-end apply pipeline for all "approved" jobs.
- `pipeline_start`: Kick off a full background run (Search -> Fetch JDs -> Rate -> Tailor Resumes -> Apply).
- `pipeline_status`: Check the progress of a running background task.
- `pipeline_stop`: Halt a running background pipeline.
- `get_job`: Retrieve details about a specific job URL from the local SQLite database.
