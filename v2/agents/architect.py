"""Architect Agent — spec summary → system design (Sonnet, ~2,000 token input)."""

from agents.base import BaseAgent
from context_budget import SONNET
from state import PipelineState

SYSTEM = """You are a Spring Boot architect. You receive a compressed requirements
summary and produce a full system design document.

Output format (Markdown):
## Technology Stack
- Spring Boot <version>, Java <version>, Maven
- <other dependencies with versions>

## Project Structure
<Maven directory tree>

## REST Endpoints
| Method | Path | Request Body | Response | Status Codes |
|--------|------|-------------|----------|--------------|

## JPA Entities
<ClassName>:
  - field: type (constraints)
  Relationships: ...

## Configuration (application.yml)
<key: value pairs>

## Package Design
- com.example.<module>: <responsibility>

Prefer H2 in-memory DB, Lombok, constructor injection."""


class ArchitectAgent(BaseAgent):
    MODEL = SONNET

    def run(self, state: PipelineState) -> str:
        """Returns full architecture text. Caller writes to state.raw.architecture."""
        print("  [Architect] Generating system design from compressed spec...")
        prompt = (
            "## Compressed Specification\n"
            f"{state.compressed.spec_summary}\n\n"
            "Produce the full system design document."
        )
        return self._run(prompt, system_prompt=SYSTEM, budget_key="architect")
