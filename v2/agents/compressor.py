"""
Compressor Agent — Memory Compression Layer (Sonnet).

Converts full RAW content into token-efficient COMPRESSED summaries.
This is the only agent that reads full content; all downstream agents
receive compressed representations only.

Target output sizes:
    prd_summary  : ~200 tokens
    spec_summary : ~300 tokens
    arch_summary : ~200 tokens
    file entry   : ~10–15 tokens
"""

from typing import Optional
from agents.base import BaseAgent
from context_budget import SONNET, TokenLedger
from state import RawState

SYSTEM = """You are a context compressor for an LLM pipeline. Your sole job is to
produce the SHORTEST possible summary that preserves all semantically important
technical details. Downstream LLM agents will use your output as their ONLY source
of context — full documents are never shown to them.

CRITICAL RULES:
- Never exceed the token budget stated in the prompt
- Use terse bullet points; no prose, no transitions, no filler
- Preserve ALL: field names, types, HTTP methods, status codes, enum values,
  package names, version numbers, constraint values
- Omit: background context, motivation paragraphs, repeated information
- Use abbreviations where unambiguous (e.g. "req" for requirement)"""


class CompressorAgent(BaseAgent):
    MODEL = SONNET

    def compress_prd(self, raw: RawState) -> str:
        """Full PRD → ~200-token bullet summary."""
        prompt = (
            "Compress the following PRD to ≤200 tokens. Use this exact structure:\n"
            "Goal: <one sentence>\n"
            "Features:\n- <bullet per feature>\n"
            "API: <HTTP method path> x N\n"
            "Tech: <stack>\n"
            "Out of scope: <exclusions>\n\n"
            f"## PRD\n{raw.prd}"
        )
        return self._run(prompt, system_prompt=SYSTEM, budget_key="compressor_prd")

    def compress_spec(self, raw: RawState) -> str:
        """Full spec → ~300-token requirements list."""
        prompt = (
            "Compress the following specification to ≤300 tokens.\n"
            "Format each requirement as: REQ-N: <terse statement>\n"
            "Then list acceptance criteria as: AC-N: <pass/fail criterion>\n"
            "Omit all prose.\n\n"
            f"## Specification\n{raw.spec}"
        )
        return self._run(prompt, system_prompt=SYSTEM, budget_key="compressor_spec")

    def compress_architecture(self, raw: RawState) -> str:
        """Full architecture doc → ~200-token component map."""
        prompt = (
            "Compress the following architecture doc to ≤200 tokens.\n"
            "Use this format:\n"
            "Stack: <tech@version list>\n"
            "Endpoints: <METHOD /path> x N\n"
            "Entities: <ClassName(field:type, ...)> x N\n"
            "Packages: <package.path: purpose> x N\n"
            "Config: <key=value> x N\n\n"
            f"## Architecture\n{raw.architecture}"
        )
        return self._run(prompt, system_prompt=SYSTEM, budget_key="compressor_arch")

    def compress_file(self, path: str, content: str) -> str:
        """Single file → one-line semantic summary (~10–15 tokens)."""
        prompt = (
            "Summarize this file in ONE line (≤15 tokens). "
            "Include: class/interface name, key methods/endpoints, main purpose.\n\n"
            f"File: {path}\n\n{content[:3000]}"  # cap input to control cost
        )
        result = self._run(prompt, system_prompt=SYSTEM, budget_key="compressor_file")
        # Ensure it stays on one line
        return result.strip().split("\n")[0]
