# Local Multi-Agent SDLC

A locally runnable multi-agent system that takes a Product Requirements Document (PRD) and automatically generates a working Spring Boot codebase through a pipeline of specialized AI agents — powered by the Claude CLI.

## How It Works

```
PRD file
  └─► Planner   → structured specification
  └─► Architect → system design
  └─► Builder   → Spring Boot code (writes files to disk)
  └─► Reviewer  → PASS / FAIL verdict
        ├─ PASS → done
        └─ FAIL → Fixer → (back to Reviewer, up to N times)
```

Each agent is a separate Claude CLI invocation with a focused role and only the tools it needs.

| Agent | Role | Tools |
|-------|------|-------|
| **Planner** | PRD → structured spec | _(none)_ |
| **Architect** | Spec → system design | _(none)_ |
| **Builder** | Design → Spring Boot files on disk | `Write`, `Bash` |
| **Reviewer** | Validates code against PRD | `Read`, `Glob`, `Grep` |
| **Fixer** | Applies minimal targeted fixes | `Read`, `Glob`, `Grep`, `Edit`, `Write` |

## Prerequisites

- **macOS / Linux** with Python 3.9+
- **Claude Code CLI** installed and logged in

```bash
# Install Claude Code CLI
npm install -g @anthropic-ai/claude-code

# Log in (one-time)
claude login
```

## Setup

```bash
git clone <repo-url>
cd local-multi-agent-sdlc

# No extra packages required — only stdlib + Claude CLI
pip install -r requirements.txt   # installs anyio (optional, not used at runtime)
```

## Usage

### 1. Write your PRD

Create a plain text file describing what you want to build. See [`example_prd.txt`](./example_prd.txt) for a reference.

A good PRD includes:
- What the system does (overview)
- Functional requirements (numbered list)
- API endpoints (HTTP method, path, request/response)
- Data model (fields, types, constraints)
- Non-functional requirements (tech stack, port, DB)

### 2. Run the pipeline

```bash
python3 main.py <your_prd.txt> [max_fix_iterations]
```

**Examples:**

```bash
# Use the included example PRD, up to 3 fix iterations (default)
python3 main.py example_prd.txt

# Custom PRD with up to 5 fix iterations
python3 main.py my_project.txt 5

# Single pass — no fix loop
python3 main.py my_project.txt 1
```

### 3. Find your output

```
output/
├── spec.md              # Planner output — structured requirements
├── architecture.md      # Architect output — system design
├── code_raw.md          # Builder snapshot (all files as text)
├── audit_1.md           # Reviewer report, iteration 1
├── code_fixed_1.md      # Code after Fixer, iteration 1 (if applicable)
├── final_code.md        # Final code snapshot
└── code/                # Actual Spring Boot project files
    ├── pom.xml
    ├── src/
    │   ├── main/
    │   │   ├── java/...
    │   │   └── resources/
    │   │       └── application.yml
    │   └── test/
    └── README.md

state.json               # Full pipeline state snapshot
```

### 4. Run the generated Spring Boot project

```bash
cd output/code
mvn spring-boot:run
```

The app starts on `http://localhost:8080` by default.

## Example Console Output

```
============================================================
  LOCAL MULTI-AGENT SDLC PIPELINE
  (powered by Claude Agent SDK)
============================================================
  PRD file      : example_prd.txt
  Max fix loops : 3
  Model         : claude-opus-4-6
============================================================

[1/5] PLANNER — decomposing requirements
    ..........
  Saved spec → output/spec.md (312 words)

[2/5] ARCHITECT — generating system design
    ..............
  Saved architecture → output/architecture.md (487 words)

[3/5] BUILDER — generating initial code
    ............................
  12 file(s) written to output/code
  Saved code (initial snapshot) → output/code_raw.md (1843 words)

[4/5] REVIEWER — iteration 1/3
    .............
  Saved audit → output/audit_1.md (201 words)

  ✓ REVIEWER: PASS — done after 1 iteration(s)

============================================================
  PIPELINE COMPLETE
============================================================
  Iterations   : 1
  Spec         : output/spec.md
  Architecture : output/architecture.md
  Code files   : output/code/
  Final code   : output/final_code.md
  State        : state.json
  Time         : 94.3s
============================================================
```

## Project Structure

```
local-multi-agent-sdlc/
├── main.py              # CLI entry point
├── orchestrator.py      # Execution flow + review/fix loop
├── state.py             # Shared SDLCState dataclass
├── requirements.txt
├── example_prd.txt      # Sample PRD (task management REST API)
└── agents/
    ├── base.py          # BaseAgent — subprocess wrapper for claude --print
    ├── planner.py
    ├── architect.py
    ├── builder.py
    ├── reviewer.py
    └── fixer.py
```

## How the Claude CLI Integration Works

Each agent calls the Claude CLI in non-interactive print mode:

```
claude --print \
  --model claude-opus-4-6 \
  --output-format stream-json --verbose \
  --no-session-persistence \
  --tools "Write,Bash" \
  --append-system-prompt "..." \
  --permission-mode acceptEdits
```

The prompt is piped via stdin. The output is parsed as JSONL events; the line with `"type": "result"` contains the agent's final response.

## v1 vs v2

| | v1 | v2 |
|---|---|---|
| **Run command** | `python3 main.py <prd> [n]` | `python3 v2/main.py <prd> [n]` |
| **Output directory** | `output/` | `v2_output/` |
| **Token usage** | High — full documents sent to every agent | 70–90% lower — only compressed summaries sent |
| **State design** | Single flat `SDLCState` | Three tiers: RAW / COMPRESSED / PATCH |
| **Memory compression** | None | Compressor agent reduces PRD/spec/arch to ~200–300 token summaries |
| **Model usage** | Opus for all agents | Sonnet for planning/routing/review; Opus only for code generation |
| **Code generation** | Single Builder call for the entire codebase | Router maps requirements to files; Builder generates one file per Opus call |
| **Review** | Single Reviewer sees full codebase | Stage 1 (Sonnet, per-file) → Stage 2 (Opus, flagged files only) |
| **Fixing** | Full file content re-sent to Fixer | Fixer receives only issue list + file paths; uses Read/Edit tools surgically |
| **Cost visibility** | None | Per-agent token ledger + estimated USD cost printed at end |
| **Best for** | Simple PRDs, quick experiments | Complex PRDs, cost-sensitive runs, production use |

**Choose v1** if you want simplicity and don't mind higher token usage.  
**Choose v2** if you have a large PRD, want lower cost, or need to understand where tokens are spent.

## Tips

- **Longer PRDs produce better code.** Include specific field names, enum values, HTTP status codes, and error message formats.
- **Increase `max_iterations` for complex PRDs.** 3 is usually enough; set 5 for large projects.
- **Re-run from scratch** by deleting `output/` and `state.json` before the next run.
- **Inspect intermediate artifacts.** `output/audit_1.md` shows exactly what the Reviewer found — useful for understanding why a fix loop triggered.

## Limitations

- Generates Spring Boot (Java/Maven) projects only.
- Requires Claude Code CLI to be installed and authenticated.
- No support for resuming a partially completed pipeline run.
- Generated code compiles in most cases but may need minor adjustments for production use.
