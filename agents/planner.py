"""Planner Agent: PRD → structured specification."""

from state import SDLCState
from agents.base import BaseAgent

SYSTEM = """You are a senior product manager and requirements engineer.

Decompose the PRD into a precise Markdown specification with these sections:
1. **Overview** – one-paragraph summary
2. **Functional Requirements** – numbered, concrete, testable features
3. **Non-Functional Requirements** – performance, security, scalability
4. **User Stories** – "As a <role>, I want <feature> so that <benefit>"
5. **Acceptance Criteria** – pass/fail criteria per requirement
6. **Out of Scope** – explicitly list what is NOT being built

Be specific. Every requirement must be testable."""


class PlannerAgent(BaseAgent):
    def run(self, state: SDLCState) -> None:
        print("  [Planner] Decomposing PRD into structured spec...")
        state.spec = self._run(
            prompt=f"## PRD\n\n{state.prd}\n\nProduce the structured specification.",
            system_prompt=SYSTEM,
            agent_name="planner",
        )
