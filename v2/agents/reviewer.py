"""
Two-Stage Reviewer — context-isolated code validation.

Stage 1 (Sonnet): Lightweight per-file check.
    Input per call : single file content + its relevant requirements
    Context        : ~800–2,500 tokens
    Output         : STATUS: PASS | FAIL + issue list for this file

Stage 2 (Opus): Deep review of flagged files only.
    Input          : flagged file contents + stage-1 issues
    Context        : ~2,000–6,000 tokens  (never the full repo)
    Output         : VERDICT: PASS | FAIL + consolidated issue list

Guardrail: neither stage ever receives the full codebase.
"""

import os
from typing import List, Tuple

from agents.base import BaseAgent
from context_budget import SONNET, OPUS
from state import PipelineState

# ── Stage 1 ────────────────────────────────────────────────────────────────────

STAGE1_SYSTEM = """You are a code reviewer performing a FOCUSED check on a single
file against its specific requirements. Do NOT speculate about files you have
not been shown.

Your response MUST follow this exact format:
STATUS: PASS
or
STATUS: FAIL
ISSUES:
- <concrete issue referencing the requirement it violates>
- ...

Be terse. Only flag definite problems, not style preferences."""


class Stage1Reviewer(BaseAgent):
    MODEL = SONNET

    def review_file(
        self,
        path: str,
        content: str,
        requirements: List[str],
        spec_summary: str,
    ) -> Tuple[bool, List[str]]:
        """
        Review a single file. Returns (passed, issues).
        requirements: list of REQ-N ids relevant to this file.
        """
        # Extract only the relevant requirement lines from the summary
        req_lines = [
            line for line in spec_summary.splitlines()
            if any(r in line for r in requirements)
        ] if requirements else []
        req_block = "\n".join(req_lines) if req_lines else "(no specific requirements mapped)"

        prompt = (
            f"## File: {path}\n\n"
            f"```\n{content[:4000]}\n```\n\n"   # cap at 4K chars to respect budget
            f"## Relevant Requirements\n{req_block}\n\n"
            "Review this file against its requirements and output your verdict."
        )
        result = self._run(
            prompt, system_prompt=STAGE1_SYSTEM, budget_key="reviewer_stage1"
        )

        passed = result.strip().startswith("STATUS: PASS")
        issues = _extract_issues(result)
        return passed, issues


# ── Stage 2 ────────────────────────────────────────────────────────────────────

STAGE2_SYSTEM = """You are a senior code reviewer performing a deep review of files
that failed an initial lightweight check. You receive only the flagged files and
their known issues — not the full codebase.

Your response MUST start with exactly one of:
VERDICT: PASS
VERDICT: FAIL

Then provide:
ISSUES:
- <file>: <specific problem referencing requirement>

RECOMMENDATIONS:
- <file>: <minimal fix description>

PASS only if all listed stage-1 issues are actually resolved or were false positives."""


class Stage2Reviewer(BaseAgent):
    MODEL = OPUS

    def review_flagged(
        self,
        flagged: List[Tuple[str, str, List[str]]],  # (path, content, issues)
        state: PipelineState,
    ) -> Tuple[str, List[str]]:
        """
        Deep review of only the flagged files.
        Returns (verdict, consolidated_issues).
        """
        file_blocks = []
        for path, content, issues in flagged:
            issue_text = "\n".join(f"  - {i}" for i in issues)
            file_blocks.append(
                f"### {path}\nStage-1 issues:\n{issue_text}\n\n"
                f"```\n{content[:3000]}\n```"  # cap per file
            )

        prompt = (
            "## Architecture Context\n"
            f"{state.compressed.arch_summary}\n\n"
            "## Flagged Files\n\n"
            + "\n\n".join(file_blocks)
            + "\n\nProvide your deep-review verdict."
        )
        result = self._run(
            prompt, system_prompt=STAGE2_SYSTEM, budget_key="reviewer_stage2"
        )

        passed = result.strip().startswith("VERDICT: PASS")
        verdict = "PASS" if passed else "FAIL"
        issues = _extract_issues(result)
        return verdict, issues


# ── Facade ─────────────────────────────────────────────────────────────────────

class ReviewerAgent:
    """Orchestrates the two-stage review process."""

    def __init__(self, ledger=None) -> None:
        self.stage1 = Stage1Reviewer(ledger=ledger)
        self.stage2 = Stage2Reviewer(ledger=ledger)

    def run(
        self, state: PipelineState, code_dir: str
    ) -> Tuple[str, List[str], List[str]]:
        """
        Returns (verdict, consolidated_issues, flagged_paths).
        verdict: 'PASS' | 'FAIL'
        """
        print(f"  [Reviewer S1/Sonnet] Checking {len(state.file_plan)} file(s)...")

        flagged: List[Tuple[str, str, List[str]]] = []

        for file_spec in state.file_plan:
            path = file_spec["path"]
            full_path = os.path.join(code_dir, path)
            if not os.path.isfile(full_path):
                print(f"    skip (not found): {path}")
                continue

            with open(full_path) as f:
                content = f.read()

            reqs = file_spec.get("requirements", [])
            passed, issues = self.stage1.review_file(
                path, content, reqs, state.compressed.spec_summary
            )
            if not passed:
                print(f"    ✗ FAIL: {path} ({len(issues)} issue(s))")
                flagged.append((path, content, issues))
            else:
                print(f"    ✓ PASS: {path}")

        if not flagged:
            return "PASS", [], []

        flagged_paths = [p for p, _, _ in flagged]
        print(
            f"\n  [Reviewer S2/Opus] Deep review of "
            f"{len(flagged)} flagged file(s)..."
        )
        verdict, issues = self.stage2.review_flagged(flagged, state)
        return verdict, issues, flagged_paths


# ── Helpers ────────────────────────────────────────────────────────────────────

def _extract_issues(text: str) -> List[str]:
    """Parse bullet-point issues from reviewer output."""
    issues = []
    in_issues = False
    for line in text.splitlines():
        if "ISSUES:" in line or "issues:" in line.lower():
            in_issues = True
            continue
        if in_issues:
            stripped = line.strip()
            if stripped.startswith("-"):
                issues.append(stripped[1:].strip())
            elif stripped and not stripped.startswith("RECOMMEND"):
                continue  # skip blank lines
            elif "RECOMMEND" in stripped.upper():
                break
    return issues
