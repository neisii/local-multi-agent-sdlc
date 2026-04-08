"""Reviewer Agent: PRD + code files → PASS/FAIL audit report."""

from state import SDLCState
from agents.base import BaseAgent

SYSTEM = """You are a strict senior code reviewer and QA engineer.

Use Read, Glob, and Grep tools to examine the code before forming your verdict.

Evaluate:
1. **Completeness** – all functional requirements implemented?
2. **Correctness** – logic matches acceptance criteria?
3. **API coverage** – all required endpoints present and correct?
4. **Data model** – entities match the spec?
5. **Error handling** – error cases handled properly?
6. **Build readiness** – would this code compile and run?

Your response MUST start with exactly one of:
VERDICT: PASS
VERDICT: FAIL

Then provide:
- **Summary**: 2–3 sentence overview
- **Issues Found** (if FAIL): numbered list, each referencing the violated requirement
- **Recommendations**: what the fixer must address

PASS only if ALL core requirements are met and the code is runnable."""


class ReviewerAgent(BaseAgent):
    def run(self, state: SDLCState, code_dir: str) -> tuple[str, bool]:
        """Return (audit_text, passed)."""
        print("  [Reviewer] Validating code against PRD...")
        audit = self._run(
            prompt=(
                f"## Original PRD\n\n{state.prd}\n\n"
                f"## Code Location\nFiles are in: {code_dir}\n\n"
                "Use Read and Glob to examine the code files, then provide your verdict."
            ),
            tools=["Read", "Glob", "Grep"],
            cwd=code_dir,
            system_prompt=SYSTEM,
        )
        passed = audit.strip().startswith("VERDICT: PASS")
        state.audit = audit
        return audit, passed
