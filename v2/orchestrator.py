"""
v2 Orchestrator — context-optimized pipeline execution.

Pipeline flow:
  PRD
   → Compressor (PRD → prd_summary)
   → Planner    (prd_summary → spec)
   → Compressor (spec → spec_summary)
   → Architect  (spec_summary → architecture)
   → Compressor (architecture → arch_summary)
   → Router     (prd_summary + arch_summary → file_plan)
   → Builder    (per-file: file_spec + arch_summary → content)  [Opus]
   → Reviewer S1 (per-file: content + requirements → PASS/FAIL) [Sonnet]
     └─ if any FAIL:
   → Reviewer S2 (flagged files + S1 issues → VERDICT)          [Opus]
     └─ if FAIL:
   → Fixer       (issues list + flagged paths → Edit calls)     [Opus]
     └─ repeat up to max_iterations
   → DONE
"""

import os
from context_budget import TokenLedger
from state import PipelineState
from agents import (
    CompressorAgent,
    PlannerAgent,
    ArchitectAgent,
    RouterAgent,
    BuilderAgent,
    ReviewerAgent,
    FixerAgent,
)
from agents.builder import write_file

MAX_ITERATIONS = 3


class Orchestrator:
    def __init__(self, max_iterations: int = MAX_ITERATIONS) -> None:
        self.max_iterations = max_iterations
        self.ledger = TokenLedger()

        self.compressor = CompressorAgent(ledger=self.ledger)
        self.planner    = PlannerAgent(ledger=self.ledger)
        self.architect  = ArchitectAgent(ledger=self.ledger)
        self.router     = RouterAgent(ledger=self.ledger)
        self.builder    = BuilderAgent(ledger=self.ledger)
        self.reviewer   = ReviewerAgent(ledger=self.ledger)
        self.fixer      = FixerAgent(ledger=self.ledger)

    def run(self, prd: str) -> PipelineState:
        state = PipelineState()
        state.raw.prd = prd
        os.makedirs("v2_output", exist_ok=True)
        code_dir = os.path.abspath("v2_output/code")
        os.makedirs(code_dir, exist_ok=True)

        # ── 0. Compress PRD ────────────────────────────────────────────────
        print("\n[0] COMPRESSOR — compressing PRD")
        state.compressed.prd_summary = self.compressor.compress_prd(state.raw)
        _save("v2_output/prd_summary.md", state.compressed.prd_summary, "prd_summary")

        # ── 1. Plan ────────────────────────────────────────────────────────
        print("\n[1] PLANNER — generating spec (Sonnet, compressed input)")
        state.raw.spec = self.planner.run(state)
        _save("v2_output/spec.md", state.raw.spec, "spec")

        print("\n    COMPRESSOR — compressing spec")
        state.compressed.spec_summary = self.compressor.compress_spec(state.raw)
        _save("v2_output/spec_summary.md", state.compressed.spec_summary, "spec_summary")

        # ── 2. Architect ───────────────────────────────────────────────────
        print("\n[2] ARCHITECT — generating system design (Sonnet, compressed input)")
        state.raw.architecture = self.architect.run(state)
        _save("v2_output/architecture.md", state.raw.architecture, "architecture")

        print("\n    COMPRESSOR — compressing architecture")
        state.compressed.arch_summary = self.compressor.compress_architecture(state.raw)
        _save("v2_output/arch_summary.md", state.compressed.arch_summary, "arch_summary")

        # ── 3. Route ───────────────────────────────────────────────────────
        print("\n[3] ROUTER — mapping requirements to files (Sonnet)")
        state.file_plan = self.router.run(state)
        _save(
            "v2_output/file_plan.json",
            __import__("json").dumps(state.file_plan, indent=2),
            f"file_plan ({len(state.file_plan)} files)",
        )

        # ── 4. Build (per-file, Opus) ──────────────────────────────────────
        print(f"\n[4] BUILDER — generating {len(state.file_plan)} file(s) (Opus per-file)")
        for i, file_spec in enumerate(state.file_plan, 1):
            path = file_spec["path"]
            print(f"  [{i}/{len(state.file_plan)}] {path}")
            content = self.builder.run_file(file_spec, state)
            state.raw.files[path] = content
            state.compressed.file_map[path] = file_spec["purpose"]
            write_file(code_dir, path, content)

        # ── 5/6/7. Review + Fix loop ───────────────────────────────────────
        while state.patch.iteration < self.max_iterations:
            state.patch.iteration += 1
            n = state.patch.iteration

            print(f"\n[5] REVIEWER — iteration {n}/{self.max_iterations}")
            verdict, issues, flagged = self.reviewer.run(state, code_dir)
            state.patch.verdict = verdict
            state.patch.issues = issues
            state.patch.flagged_files = flagged
            _save(f"v2_output/audit_{n}.md", _format_audit(verdict, issues, flagged), f"audit #{n}")
            state.save("v2_output/state.json")

            if verdict == "PASS":
                print(f"\n  ✓ PASS — pipeline complete after {n} iteration(s)")
                break

            if n >= self.max_iterations:
                print(f"\n  ✗ FAIL — max iterations ({self.max_iterations}) reached")
                break

            print(f"\n[6] FIXER — patching {len(flagged)} file(s) (Opus, diff-based)")
            self.fixer.run(state, code_dir, flagged, issues)

        # ── Final save ─────────────────────────────────────────────────────
        state.save("v2_output/state.json")
        return state

    def cost_report(self) -> str:
        return self.ledger.report()


def _save(path: str, content: str, label: str) -> None:
    with open(path, "w") as f:
        f.write(content)
    from context_budget import estimate_tokens
    print(f"  Saved {label} → {path} (~{estimate_tokens(content):,} tokens)")


def _format_audit(verdict: str, issues: list, flagged: list) -> str:
    lines = [f"VERDICT: {verdict}", ""]
    if flagged:
        lines += ["## Flagged Files", *[f"- {p}" for p in flagged], ""]
    if issues:
        lines += ["## Issues", *[f"- {i}" for i in issues]]
    return "\n".join(lines)
