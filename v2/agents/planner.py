"""Planner Agent — PRD summary → structured spec (Sonnet, ~1,500 token input)."""

from agents.base import BaseAgent
from context_budget import SONNET
from state import PipelineState

SYSTEM = """You are a requirements engineer. You receive a compressed PRD summary
(not the full PRD) and produce a full structured specification.

Output format (Markdown):
## Requirements
REQ-1: <concrete, testable requirement>
REQ-2: ...

## Acceptance Criteria
AC-1 (REQ-1): <pass/fail criterion>
AC-2 (REQ-2): ...

## Non-Functional Requirements
- <performance / security / tech constraints>

## Out of Scope
- <explicit exclusions>

Be specific. Every requirement must map to at least one acceptance criterion."""


class PlannerAgent(BaseAgent):
    MODEL = SONNET

    def run(self, state: PipelineState) -> str:
        """Returns full spec text. Caller writes to state.raw.spec."""
        print("  [Planner] Generating spec from compressed PRD...")
        prompt = (
            "## Compressed PRD\n"
            f"{state.compressed.prd_summary}\n\n"
            "Produce the full structured specification."
        )
        return self._run(prompt, system_prompt=SYSTEM, budget_key="planner")
