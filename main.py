"""Entry point: reads a PRD file and runs the multi-agent SDLC pipeline."""

import sys
import time
from orchestrator import Orchestrator


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python main.py <prd_file> [max_iterations]")
        print("Example: python main.py example_prd.txt 3")
        sys.exit(1)

    prd_file = sys.argv[1]
    max_iterations = int(sys.argv[2]) if len(sys.argv) > 2 else 3

    try:
        with open(prd_file) as f:
            prd = f.read().strip()
    except FileNotFoundError:
        print(f"Error: PRD file not found: {prd_file}")
        sys.exit(1)

    if not prd:
        print("Error: PRD file is empty")
        sys.exit(1)

    print("=" * 60)
    print("  LOCAL MULTI-AGENT SDLC PIPELINE")
    print("  (powered by Claude Agent SDK)")
    print("=" * 60)
    print(f"  PRD file      : {prd_file}")
    print(f"  Max fix loops : {max_iterations}")
    print(f"  Model         : claude-opus-4-6")
    print("=" * 60)

    start = time.time()
    orchestrator = Orchestrator(max_iterations=max_iterations)

    try:
        state = orchestrator.run(prd)
    except KeyboardInterrupt:
        print("\n\nInterrupted by user.")
        sys.exit(1)

    elapsed = time.time() - start
    print("\n" + "=" * 60)
    print("  PIPELINE COMPLETE")
    print("=" * 60)
    print(f"  Iterations   : {state.iteration}")
    print(f"  Spec         : output/spec.md")
    print(f"  Architecture : output/architecture.md")
    print(f"  Code files   : output/code/")
    print(f"  Final code   : output/final_code.md")
    print(f"  State        : state.json")
    print(f"  Time         : {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    main()
