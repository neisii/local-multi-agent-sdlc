"""Builder Agent: architecture + spec → Spring Boot project files on disk."""

import glob
import os
from state import SDLCState
from agents.base import BaseAgent

SYSTEM = """You are a senior Spring Boot developer. Generate a complete, runnable
Spring Boot 3.x / Java 21 Maven project by writing every file to disk.

Rules:
- Use the Write tool to write EVERY required file
- Files go in the CURRENT DIRECTORY (you are already inside output/code/)
- Include: pom.xml, src/main/resources/application.yml, all Java source files, README.md
- No placeholders or TODOs — every file must be complete and compilable
- Use constructor injection (not @Autowired on fields)
- Use Lombok (@Data, @Builder, @RequiredArgsConstructor) to reduce boilerplate
- H2 in-memory database — zero external dependencies
- Add a @ControllerAdvice for global error handling
- After writing all files, summarize what you created (file count, packages, etc.)"""


class BuilderAgent(BaseAgent):
    def run(self, state: SDLCState, code_dir: str) -> None:
        print("  [Builder] Generating Spring Boot project files...")
        os.makedirs(code_dir, exist_ok=True)

        summary = self._run(
            prompt=(
                f"## Specification\n\n{state.spec}\n\n"
                f"## Architecture\n\n{state.architecture}\n\n"
                "Write every project file to disk now using the Write tool. "
                "Start with pom.xml, then application.yml, then all Java source files."
            ),
            tools=["Write", "Bash"],
            cwd=code_dir,
            system_prompt=SYSTEM,
            permission_mode="acceptEdits",
            agent_name="builder",
        )

        state.code = _read_code_tree(code_dir)
        count = sum(1 for p in glob.glob(f"{code_dir}/**/*", recursive=True) if os.path.isfile(p))
        print(f"  [Builder] {count} file(s) written to {code_dir}")


def _read_code_tree(base_dir: str) -> str:
    """Read all text files into a single FILE-marker string for downstream agents."""
    parts = []
    for path in sorted(glob.glob(f"{base_dir}/**/*", recursive=True)):
        if not os.path.isfile(path):
            continue
        rel = os.path.relpath(path, base_dir)
        try:
            with open(path) as f:
                content = f.read()
        except (UnicodeDecodeError, OSError):
            continue
        parts.append(f"=== FILE: {rel} ===\n{content}\n=== END FILE ===")
    return "\n\n".join(parts)
