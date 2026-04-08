"""Architect Agent: spec → system design."""

from state import SDLCState
from agents.base import BaseAgent

SYSTEM = """You are a principal software architect specializing in Spring Boot.

Given a specification, produce a detailed system design Markdown document with:
1. **Technology Stack** – exact versions (Spring Boot 3.x, Java 21, etc.)
2. **System Components** – each module and its responsibility
3. **API Design** – REST endpoints with method, path, request/response shapes
4. **Data Models** – JPA entities with fields, types, and relationships
5. **Project Structure** – full Maven directory tree
6. **Key Dependencies** – pom.xml dependencies (groupId:artifactId:version)
7. **Configuration** – required application.yml properties

Prefer simplicity. Use Spring Boot starters and H2 in-memory DB."""


class ArchitectAgent(BaseAgent):
    def run(self, state: SDLCState) -> None:
        print("  [Architect] Generating system design...")
        state.architecture = self._run(
            prompt=(
                f"## Specification\n\n{state.spec}\n\n"
                "Produce the system design document."
            ),
            system_prompt=SYSTEM,
        )
