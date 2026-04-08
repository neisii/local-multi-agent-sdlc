"""
Code Router Agent — maps requirements to files (Sonnet, ~1,200 token input).

This agent is the context firewall between planning and code generation.
It produces a structured file plan that lets the Builder generate one file
at a time with only its relevant context.
"""

import json
import re
from typing import List

from agents.base import BaseAgent
from context_budget import SONNET
from state import PipelineState

SYSTEM = """You are a code routing agent. Given a compressed PRD summary and
architecture summary, output a JSON file plan for a Spring Boot Maven project.

Output ONLY a valid JSON array — no prose, no markdown fences.

Each element:
{
  "path": "relative/path/from/project/root",
  "purpose": "one sentence: what this file does and key classes/methods",
  "requirements": ["REQ-1", "REQ-2"],
  "depends_on": ["path/to/dependency.java"]
}

Rules:
- Include ALL files: pom.xml, application.yml, every .java source file
- Order by dependency (dependencies before dependents)
- Be specific in "purpose": include class names, HTTP methods, field names
- "requirements": list only directly relevant REQ-N ids
- "depends_on": only immediate compile-time dependencies"""


class RouterAgent(BaseAgent):
    MODEL = SONNET

    def run(self, state: PipelineState) -> List[dict]:
        """Returns the file plan list. Caller stores to state.file_plan."""
        print("  [Router] Mapping requirements to file structure...")
        prompt = (
            "## Compressed PRD\n"
            f"{state.compressed.prd_summary}\n\n"
            "## Compressed Architecture\n"
            f"{state.compressed.arch_summary}\n\n"
            "## Requirements Index\n"
            f"{state.compressed.spec_summary}\n\n"
            "Output the JSON file plan."
        )
        raw = self._run(prompt, system_prompt=SYSTEM, budget_key="router")
        return _parse_file_plan(raw)


def _parse_file_plan(text: str) -> List[dict]:
    """Extract JSON array from Claude's response robustly."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).replace("```", "").strip()
    # Find the outermost JSON array
    match = re.search(r"(\[.*\])", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    raise ValueError(f"Router did not return valid JSON.\nRaw output:\n{text[:500]}")
