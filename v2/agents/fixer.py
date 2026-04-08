"""
Fixer Agent — diff-based targeted fixes (Opus, file-scoped).

Key design principles:
1. The prompt contains ONLY the issue list and flagged file paths — not full content.
2. Claude uses Read + Edit tools to read files and apply surgical edits.
3. Never regenerates a file from scratch (diff-only philosophy).
4. Only flagged files are touched; other files are isolated.

Context per call: ~500 tokens of prompt + tool round-trips (no bulk injection).
"""

from typing import List
from agents.base import BaseAgent
from context_budget import OPUS
from state import PipelineState

SYSTEM = """You are a surgical code fixer. You receive a list of files and their
specific issues. Your job is to make the MINIMAL change that resolves each issue.

Rules:
- Use the Read tool to read only the files that need fixing
- Use the Edit tool to apply targeted changes (never rewrite a whole file)
- Fix EXACTLY what is reported — do not refactor unrelated code
- Do not modify files that are not listed
- After all fixes, output a concise fix log:
  ## Fix Log
  - <file>: <what changed and why (one line)>"""


class FixerAgent(BaseAgent):
    MODEL = OPUS

    def run(
        self,
        state: PipelineState,
        code_dir: str,
        flagged_paths: List[str],
        issues: List[str],
    ) -> None:
        """
        Apply minimal fixes to flagged files using Read + Edit tools.
        state.patch is updated with the fix results.
        """
        if not flagged_paths:
            return

        # Issue list — the only bulk content sent to the model
        issue_block = "\n".join(f"- {i}" for i in issues)
        file_list = "\n".join(f"- {p}" for p in flagged_paths)

        prompt = (
            "## Architecture Context\n"
            f"{state.compressed.arch_summary}\n\n"
            "## Files To Fix\n"
            f"{file_list}\n\n"
            "## Issues To Resolve\n"
            f"{issue_block}\n\n"
            "Use Read to inspect each file, then Edit to apply the minimal fix. "
            "Output your fix log when done."
        )

        self._run(
            prompt=prompt,
            tools=["Read", "Edit", "Glob"],
            cwd=code_dir,
            system_prompt=SYSTEM,
            permission_mode="acceptEdits",
            budget_key="fixer",
        )

        # Update compressed file_map for any patched files
        _refresh_file_map(state, code_dir, flagged_paths)


def _refresh_file_map(
    state: PipelineState, code_dir: str, patched_paths: List[str]
) -> None:
    """Update one-liner summaries for patched files in the compressed state."""
    import os
    for rel_path in patched_paths:
        full = os.path.join(code_dir, rel_path)
        if not os.path.isfile(full):
            continue
        # Mark as patched without re-running the compressor (cost optimization)
        old = state.compressed.file_map.get(rel_path, "")
        state.compressed.file_map[rel_path] = old + " [patched]"
