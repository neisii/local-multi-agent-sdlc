"""Base agent: drives the Claude CLI via subprocess (stream-json output)."""

import json
import subprocess
from typing import Dict, List, Optional, Tuple


def _estimate_tokens(text: str) -> int:
    """Rough estimate: 1 token ≈ 0.75 words."""
    return int(len(text.split()) / 0.75)


class TokenLedger:
    """Tracks cumulative token usage and estimated cost across the pipeline."""

    # v1 uses Opus for every agent
    _COST_INPUT_PER_1M  = 25.0
    _COST_OUTPUT_PER_1M = 75.0

    def __init__(self) -> None:
        self._calls: List[Tuple[str, int, int]] = []   # (agent, in_tok, out_tok)

    def record(self, agent: str, prompt: str, output: str) -> None:
        self._calls.append((agent, _estimate_tokens(prompt), _estimate_tokens(output)))

    def report(self) -> str:
        total_in = total_out = 0
        lines = [
            f"{'Agent':<22} {'In':>8} {'Out':>8}",
            "-" * 42,
        ]
        for agent, in_tok, out_tok in self._calls:
            lines.append(f"{agent:<22} {in_tok:>8,} {out_tok:>8,}")
            total_in  += in_tok
            total_out += out_tok

        total_all  = total_in + total_out
        cost = (total_in * self._COST_INPUT_PER_1M + total_out * self._COST_OUTPUT_PER_1M) / 1_000_000

        lines += [
            "=" * 42,
            f"{'TOTAL':<22} {total_in:>8,} {total_out:>8,}",
            f"{'ALL TOKENS':<22} {total_all:>8,}",
            "",
            f"  Model         : claude-opus-4-6",
            f"  Estimated cost: ${cost:.4f}",
        ]
        return "\n".join(lines)


class BaseAgent:
    MODEL = "claude-opus-4-6"

    def __init__(self, ledger: Optional[TokenLedger] = None) -> None:
        self.ledger = ledger

    def _run(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        system_prompt: Optional[str] = None,
        permission_mode: str = "default",
        agent_name: Optional[str] = None,
    ) -> str:
        """Invoke `claude --print` and return the final result text."""
        cmd = [
            "claude",
            "--print",
            "--model", self.MODEL,
            "--output-format", "stream-json",
            "--verbose",
            "--no-session-persistence",
        ]

        if tools:
            cmd += ["--tools", ",".join(tools)]
        else:
            cmd += ["--tools", ""]  # disable all built-in tools

        if system_prompt:
            cmd += ["--append-system-prompt", system_prompt]

        if permission_mode != "default":
            cmd += ["--permission-mode", permission_mode]

        print("    ", end="", flush=True)
        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
        )

        # Write prompt and close stdin so claude receives EOF
        proc.stdin.write(prompt)
        proc.stdin.close()

        result = ""
        for raw_line in proc.stdout:
            line = raw_line.strip()
            if not line:
                continue
            print(".", end="", flush=True)
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue

            if event.get("type") == "result":
                result = event.get("result", "")
                if event.get("is_error"):
                    raise RuntimeError(f"Claude returned error: {result}")

        proc.wait()
        print()  # newline after dots

        if proc.returncode != 0 and not result:
            stderr = proc.stderr.read()
            raise RuntimeError(
                f"Claude CLI exited with rc={proc.returncode}: {stderr[:500]}"
            )

        if self.ledger is not None:
            self.ledger.record(agent_name or self.__class__.__name__, prompt, result)

        return result
