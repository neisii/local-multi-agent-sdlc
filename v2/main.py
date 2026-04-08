"""v2 entry point — context-optimized multi-agent SDLC pipeline."""

import sys
import time
import os

# Add v2/ to path so agents can import from context_budget and state
sys.path.insert(0, os.path.dirname(__file__))

from orchestrator import Orchestrator


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python v2/main.py <prd_file> [max_iterations]")
        print("Example: python v2/main.py example_prd.txt 3")
        sys.exit(1)

    prd_file = sys.argv[1]
    max_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    try:
        with open(prd_file) as f:
            prd = f.read().strip()
    except FileNotFoundError:
        print(f"Error: PRD file not found: {prd_file}")
        sys.exit(1)

    print("=" * 64)
    print("  CONTEXT-OPTIMIZED MULTI-AGENT SDLC PIPELINE  (v2)")
    print("=" * 64)
    print(f"  PRD file      : {prd_file}")
    print(f"  Max fix loops : {max_iterations}")
    print(f"  Sonnet agents : Compressor, Planner, Architect, Router, Reviewer-S1")
    print(f"  Opus agents   : Builder (per-file), Reviewer-S2, Fixer")
    print("=" * 64)

    start = time.time()
    orchestrator = Orchestrator(max_iterations=max_iterations)

    try:
        state = orchestrator.run(prd)
    except KeyboardInterrupt:
        print("\n\nInterrupted.")
        sys.exit(1)

    elapsed = time.time() - start

    print("\n" + "=" * 64)
    print("  PIPELINE COMPLETE")
    print("=" * 64)
    print(f"  Iterations      : {state.patch.iteration}")
    print(f"  Final verdict   : {state.patch.verdict or 'PASS'}")
    print(f"  Files generated : {len(state.file_plan)}")
    print(f"  Code output     : v2_output/code/")
    print(f"  Artifacts       : v2_output/")
    print(f"  State snapshot  : v2_output/state.json")
    print(f"  Total time      : {elapsed:.1f}s")
    print("=" * 64)
    print("\n── Token & Cost Report ──────────────────────────────────────")
    print(orchestrator.cost_report())
    print("─" * 64)


if __name__ == "__main__":
    main()
