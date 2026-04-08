"""
Three-tier state design for the context-optimized SDLC pipeline.

RAW   — immutable source of truth, never sent to LLMs directly
COMPRESSED — LLM-input-optimized summaries, sent to most agents
PATCH — diff-only updates for the current review/fix iteration
"""

import json
from dataclasses import dataclass, field
from typing import Dict, List


# ── Tier 1: RAW (immutable) ────────────────────────────────────────────────────

@dataclass
class RawState:
    """Full, unmodified content. Never injected wholesale into any LLM prompt."""
    prd: str = ""
    spec: str = ""
    architecture: str = ""
    files: Dict[str, str] = field(default_factory=dict)   # path → full content
    audit_history: List[str] = field(default_factory=list) # one entry per iteration


# ── Tier 2: COMPRESSED (LLM-optimized) ────────────────────────────────────────

@dataclass
class CompressedState:
    """
    Semantic summaries produced by the Compressor agent.
    Target sizes:
        prd_summary  ~200 tokens
        spec_summary ~300 tokens
        arch_summary ~200 tokens
        file_map     ~10-15 tokens per file entry
    """
    prd_summary: str = ""
    spec_summary: str = ""
    arch_summary: str = ""
    file_map: Dict[str, str] = field(default_factory=dict)  # path → one-liner
    current_issues: List[str] = field(default_factory=list)


# ── Tier 3: PATCH (diff-only) ─────────────────────────────────────────────────

@dataclass
class PatchState:
    """Tracks only what changed in the current iteration — not full content."""
    iteration: int = 0
    verdict: str = ""                        # PASS | FAIL | ""
    flagged_files: List[str] = field(default_factory=list)  # paths with issues
    issues: List[str] = field(default_factory=list)         # structured issue list


# ── Unified Pipeline State ─────────────────────────────────────────────────────

@dataclass
class PipelineState:
    raw: RawState = field(default_factory=RawState)
    compressed: CompressedState = field(default_factory=CompressedState)
    patch: PatchState = field(default_factory=PatchState)
    file_plan: List[dict] = field(default_factory=list)  # router output

    def save(self, path: str = "state_v2.json") -> None:
        """Persist a debug-friendly snapshot (raw content stored separately)."""
        data = {
            "compressed": {
                "prd_summary": self.compressed.prd_summary,
                "spec_summary": self.compressed.spec_summary,
                "arch_summary": self.compressed.arch_summary,
                "file_map": self.compressed.file_map,
                "current_issues": self.compressed.current_issues,
            },
            "patch": {
                "iteration": self.patch.iteration,
                "verdict": self.patch.verdict,
                "flagged_files": self.patch.flagged_files,
                "issues": self.patch.issues,
            },
            "raw_index": {
                "prd_chars": len(self.raw.prd),
                "spec_chars": len(self.raw.spec),
                "arch_chars": len(self.raw.architecture),
                "files": list(self.raw.files.keys()),
            },
            "file_plan": self.file_plan,
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


# ── JSON Schemas (reference) ───────────────────────────────────────────────────

RAW_SCHEMA = {
    "prd": "string",
    "spec": "string",
    "architecture": "string",
    "files": {"<path>": "<full_content>"},
    "audit_history": ["string"],
}

COMPRESSED_SCHEMA = {
    "prd_summary": "string (~200 tokens)",
    "spec_summary": "string (~300 tokens)",
    "arch_summary": "string (~200 tokens)",
    "file_map": {"<path>": "string (one-liner, ~10-15 tokens)"},
    "current_issues": ["string"],
}

PATCH_SCHEMA = {
    "iteration": "int",
    "verdict": "PASS | FAIL | ''",
    "flagged_files": ["<path>"],
    "issues": ["string"],
}

FILE_PLAN_SCHEMA = [
    {
        "path": "relative/path/to/File.java",
        "purpose": "one-sentence description",
        "requirements": ["REQ-1", "REQ-2"],
        "depends_on": ["relative/path/to/Dependency.java"],
    }
]
