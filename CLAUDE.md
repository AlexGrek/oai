# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

| Command | Description |
|---|---|
| `task run` | Start the FastAPI server |
| `task dev` | Start with auto-reload |
| `task test` | Run the integration test script |
| `task fmt` | Format code with black |
| `task install` | Install all dependencies |

**Add a dependency:**
```bash
pdm add <package>          # runtime
pdm add -dG dev <package>  # dev only
```

## Architecture

This is a FastAPI-based LLM pipeline execution proxy. It accepts YAML-defined pipelines, submits queries to an external **OffloadMQ** backend, and orchestrates multi-step LLM workflows.

### Request Flow

1. Client authenticates via `/api/v1/login` using a token from `OAI_TOKENS` env var
2. Client POSTs a pipeline payload to `/api/v1/post`
3. `engine/taskmaster.py` orchestrates execution — it loads the pipeline, resolves steps, and delegates to `engine/pipelines/exec.py`
4. Each pipeline step calls `engine/pipelines/query_send.py`, which picks a model via `engine/model_picker.py` and submits the query to OffloadMQ via `engine/apiclient.py`
5. `engine/waiter.py` polls OffloadMQ for task completion
6. Results flow back up through the pipeline executor, applying variable substitution, conditional logic, and data extraction

### Key Concepts

**Pipelines** (`engine/pipelines/`): Defined in YAML. A pipeline has named steps, each with a list of messages (system/user) and optional `extract` rules to pull data from LLM output. Steps can reference outputs from previous steps using dot-notation (`{{step_name.field}}`). Conditional branching is supported via `if/and/or` operators.

**Data Extraction** (`engine/pipelines/exec.py`): After each LLM response, `extract` rules apply transformations: jq-style path extraction from JSON, full-text capture, and type casting (string/number/boolean). JavaScript sandbox (`engine/pipelines/scripting.py`, powered by `py_mini_racer`) handles complex extraction scripts.

**OffloadMQ Backend** (`engine/apiclient.py`): External LLM service. Configured via `OFFLOADMQ_BACKEND_URL` and `OFFLOADMQ_TOKEN`. The client submits tasks and polls for results. Capabilities (available models) are fetched once and cached.

**Authentication** (`auth.py`): Bearer token or cookie. Valid tokens are defined in `OAI_TOKENS` env var as colon-separated values. The `/api/v1/login` endpoint issues a JWT-like session token for subsequent requests.

**Pipeline Storage** (`storage/pipelines.py`): Currently loads from YAML files. The example pipeline (`pipeline_example.yaml`) implements log-line security threat analysis.

### Environment Variables

| Variable | Purpose |
|---|---|
| `OAI_TOKENS` | Colon-separated valid API tokens (e.g. `token_a:token_b`) |
| `OFFLOADMQ_TOKEN` | Auth token for the OffloadMQ backend |
| `OFFLOADMQ_BACKEND_URL` | Base URL for OffloadMQ service |
