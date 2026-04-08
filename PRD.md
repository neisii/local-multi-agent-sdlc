Prompt: Local Multi-Agent SDLC System (Minimal Implementation)

You are a senior software engineer and AI systems architect.

Your task is to build a locally runnable minimal multi-agent system for an LLM-driven software development lifecycle (SDLC).

The system must be simple, production-inspired, and runnable on a local machine without cloud infrastructure.

⸻

1. Objective

Design and implement a minimal multi-agent orchestration system that takes a PRD and automatically:
	1.	Decomposes requirements
	2.	Generates architecture
	3.	Generates code (Spring Boot preferred)
	4.	Reviews code against PRD
	5.	Applies fixes if needed (loop)

The system must be fully runnable locally.

⸻

2. Required Architecture (Minimal Version)

Implement the following agents:
	•	Planner Agent (PRD → structured requirements)
	•	Architect Agent (requirements → system design)
	•	Builder Agent (design → code)
	•	Reviewer Agent (PRD + code → validation report)
	•	Fixer Agent (audit → minimal patch)

⸻

3. Core Requirement

You MUST implement a local orchestrator that manages execution flow:

PRD
 → Planner
 → Architect
 → Builder
 → Reviewer
 → (if FAIL → Fixer → Builder loop)
 → DONE


⸻

4. Technical Constraints
	•	Language: Python (mandatory)
	•	Must run locally (no external orchestration services)
	•	Use OpenAI/Claude API wrapper OR abstract LLM interface
	•	No complex frameworks (LangGraph optional but not required)
	•	Keep dependencies minimal

⸻

5. State Management

You must implement a shared state object:

{
  "prd": "...",
  "spec": "...",
  "architecture": "...",
  "code": "...",
  "audit": "...",
  "iteration": 0
}

All agents must read/write to this state.

⸻

6. Output Requirements

Provide:

1. Project Structure
	•	Python file layout

2. Core Orchestrator Code
	•	main loop
	•	iteration control
	•	agent execution flow

3. Agent Implementations

Each agent must be a separate module or class:
	•	planner.py
	•	architect.py
	•	builder.py
	•	reviewer.py
	•	fixer.py

4. Prompt Definitions

Each agent must have a clearly defined prompt.

5. Runnable Example
	•	Example PRD input
	•	Example execution flow

⸻

7. Design Rules
	•	Keep it minimal (MVP only)
	•	No over-engineering
	•	No distributed systems
	•	No Kubernetes, no message queues
	•	Focus on clarity and debuggability

⸻

8. Success Criteria

The system is correct if:
	•	A PRD can be input as a text file
	•	The system generates code through multiple agents
	•	Reviewer can detect issues
	•	Fixer can improve output iteratively
	•	Final output is a working codebase

⸻

9. Important Constraint

Do NOT design a theoretical system.

You MUST produce actual runnable Python code.

⸻

END

This is a minimal local multi-agent SDLC automation system.
