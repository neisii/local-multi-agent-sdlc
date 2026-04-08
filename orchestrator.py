"""Orchestrator: manages agent execution flow and the review/fix loop."""

import os
from state import SDLCState
from agents import (
    PlannerAgent,
    ArchitectAgent,
    BuilderAgent,
    ReviewerAgent,
    FixerAgent,
)

MAX_ITERATIONS = 3


class Orchestrator:
    def __init__(self, max_iterations: int = MAX_ITERATIONS) -> None:
        self.max_iterations = max_iterations
        self.planner = PlannerAgent()
        self.architect = ArchitectAgent()
        self.builder = BuilderAgent()
        self.reviewer = ReviewerAgent()
        self.fixer = FixerAgent()

    def run(self, prd: str) -> SDLCState:
        state = SDLCState(prd=prd)
        os.makedirs("output", exist_ok=True)
        code_dir = os.path.abspath("output/code")
        os.makedirs(code_dir, exist_ok=True)

        # ── Phase 1: Plan ──────────────────────────────────────────────────
        print("\n[1/5] PLANNER — decomposing requirements")
        self.planner.run(state)
        _save("output/spec.md", state.spec, "spec")

        # ── Phase 2: Architect ─────────────────────────────────────────────
        print("\n[2/5] ARCHITECT — generating system design")
        self.architect.run(state)
        _save("output/architecture.md", state.architecture, "architecture")

        # ── Phase 3: Build ─────────────────────────────────────────────────
        print("\n[3/5] BUILDER — generating initial code")
        self.builder.run(state, code_dir)
        _save("output/code_raw.md", state.code, "code (initial snapshot)")

        # ── Phase 4/5: Review + Fix loop ───────────────────────────────────
        while state.iteration < self.max_iterations:
            state.iteration += 1
            print(f"\n[4/5] REVIEWER — iteration {state.iteration}/{self.max_iterations}")
            audit, passed = self.reviewer.run(state, code_dir)
            _save(f"output/audit_{state.iteration}.md", audit, "audit")
            state.save("state.json")

            if passed:
                print(f"\n  ✓ REVIEWER: PASS — done after {state.iteration} iteration(s)")
                break

            if state.iteration >= self.max_iterations:
                print(f"\n  ✗ REVIEWER: FAIL — max iterations reached")
                break

            print(f"\n[5/5] FIXER — applying fixes (iteration {state.iteration})")
            self.fixer.run(state, code_dir)
            _save(f"output/code_fixed_{state.iteration}.md", state.code, f"code (fixed #{state.iteration})")

        # ── Final save ─────────────────────────────────────────────────────
        state.save("state.json")
        _save("output/final_code.md", state.code, "final code snapshot")
        return state


def _save(path: str, content: str, label: str) -> None:
    with open(path, "w") as f:
        f.write(content)
    print(f"  Saved {label} → {path} ({len(content.split())} words)")
