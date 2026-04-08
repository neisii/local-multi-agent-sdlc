"""Fixer Agent: applies targeted fixes to code files based on the audit."""

from state import SDLCState
from agents.base import BaseAgent
from agents.builder import _read_code_tree

SYSTEM = """You are a senior developer applying minimal, targeted fixes to a
Spring Boot project based on a code review audit.

Use Read, Glob, Grep, Edit, and Write tools to:
1. Read files flagged in the audit
2. Make the SMALLEST change that resolves each issue
3. Do NOT modify files that are working correctly
4. Do NOT refactor unrelated code

After all fixes are applied, output a concise fix summary:
## Fix Summary
- <filename>: <what was changed and why>"""


class FixerAgent(BaseAgent):
    def run(self, state: SDLCState, code_dir: str) -> None:
        print("  [Fixer] Applying targeted fixes...")
        self._run(
            prompt=(
                f"## Audit Report\n\n{state.audit}\n\n"
                f"## Code Location\nFiles are in: {code_dir}\n\n"
                "Read the flagged files, apply minimal fixes, output your fix summary."
            ),
            tools=["Read", "Glob", "Grep", "Edit", "Write"],
            cwd=code_dir,
            system_prompt=SYSTEM,
            permission_mode="acceptEdits",
        )
        state.code = _read_code_tree(code_dir)
