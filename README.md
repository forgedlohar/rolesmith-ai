# Rolesmith AI

An LLM "autopilot" pipeline that discovers, rates, and autonomously applies to jobs across multiple platforms, intelligently tailoring your resume per application.

Rolesmith AI builds upon the foundational web automation of `job-apply-mcp`, extending it with a powerful AI agent pipeline that reasons about Job Descriptions, customizes your PDF resume via LaTeX, and completes complex application forms natively in Playwright.

## Features

- **Multi-Platform Automation**: Supports LinkedIn, Naukri, Wellfound, and Indeed India.
- **LLM-Powered Rating**: Evaluates Job Descriptions against your profile to find high-match roles and identify red flags.
- **Resume Tailoring**: Automatically highlights relevant experiences in your resume for specific applications using LaTeX compilation.
- **Smart Form Completion**: Answers dynamic application form questions accurately using context from your profile and LLM inference.
- **MCP Integration**: Fully compatible as a Model Context Protocol (MCP) server for Claude Desktop.

## Documentation

- [Configuration Guide](docs/configuration.md)
- [Usage Guide](docs/usage.md)
- [Architecture](docs/architecture.md)

## Installation

We use `uv` for reproducible environment management:

```bash
# Clone the repository
git clone https://github.com/your-username/rolesmith-ai.git
cd rolesmith-ai

# Install dependencies using uv
uv sync
```

For full installation and MCP setup instructions, see the [Usage Guide](docs/usage.md).

## Usage

You can run Rolesmith AI as a standalone CLI or connect it to Claude Desktop as an MCP server.

```bash
uv run python3 -m rolesmith_ai.pipeline discover
uv run python3 -m rolesmith_ai.pipeline tailor
uv run python3 -m rolesmith_ai.pipeline apply --live
```

## Attribution

Rolesmith AI was originally forked from [pulkit017/job-apply-mcp](https://github.com/pulkit017/job-apply-mcp). The base Playwright automation and MCP transport mechanisms were adapted from the original project. The AI pipeline (discovery, rating, tailoring, and autonomous form completion) was added as a complete autopilot layer on top.
