"""
Builder Agent — per-file code generation (Opus only).

Each call generates exactly ONE file. The orchestrator calls this N times
(once per file in the file plan) and writes each result to disk in Python.

Context per call:  ~600–800 tokens  (vs. 15,000+ in v1)
Model:             Opus             (isolated to code generation only)
"""

import os
import re
from typing import List

from agents.base import BaseAgent
from context_budget import OPUS
from state import PipelineState

SYSTEM = """You are a senior Spring Boot developer. You will be given a specification
for ONE file to generate. Output ONLY the raw file content — no markdown, no
code fences, no explanation. The output is written directly to disk.

Rules:
- Complete, compilable code — no placeholders, no TODOs
- Spring Boot 3.x, Java 21
- Constructor injection only (never @Autowired on fields)
- Lombok (@Data, @Builder, @RequiredArgsConstructor) to reduce boilerplate
- H2 in-memory DB for zero-config persistence
- For pom.xml: include spring-boot-starter-web, data-jpa, h2, validation, lombok
- For application.yml: include H2 console, JPA DDL auto=create-drop, port 8080
- For @ControllerAdvice: handle MethodArgumentNotValidException and
  ResponseStatusException with {error, message} JSON body"""


class BuilderAgent(BaseAgent):
    MODEL = OPUS   # the only Opus agent

    def run_file(self, file_spec: dict, state: PipelineState) -> str:
        """
        Generate content for a single file.
        Returns raw file content string (caller writes to disk).
        """
        path = file_spec["path"]
        purpose = file_spec["purpose"]
        reqs = file_spec.get("requirements", [])
        deps = file_spec.get("depends_on", [])

        # Build a minimal dependency context from the compressed file_map
        dep_context = ""
        if deps:
            dep_lines = [
                f"  {d}: {state.compressed.file_map.get(d, '(no summary yet)')}"
                for d in deps
            ]
            dep_context = "Dependencies (already generated):\n" + "\n".join(dep_lines)

        # Relevant requirements (subset, not all)
        req_context = ""
        if reqs:
            relevant = [
                line for line in state.compressed.spec_summary.splitlines()
                if any(r in line for r in reqs)
            ]
            req_context = "Relevant requirements:\n" + "\n".join(relevant)

        prompt = (
            f"Generate file: {path}\n"
            f"Purpose: {purpose}\n\n"
            f"## Architecture Reference\n{state.compressed.arch_summary}\n\n"
            + (f"{req_context}\n\n" if req_context else "")
            + (f"{dep_context}\n\n" if dep_context else "")
            + "Output the complete file content now."
        )

        result = self._run(prompt, system_prompt=SYSTEM, budget_key="builder_file")
        return _strip_code_fence(result)


def write_file(code_dir: str, rel_path: str, content: str) -> None:
    """Write generated file content to disk under code_dir."""
    full_path = os.path.join(code_dir, rel_path)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, "w") as f:
        f.write(content)


def _strip_code_fence(text: str) -> str:
    """Remove markdown code fences if Claude added them despite instructions."""
    lines = text.strip().split("\n")
    if lines and re.match(r"^```", lines[0]):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    return "\n".join(lines)
