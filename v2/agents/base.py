"""Base agent: Claude CLI subprocess wrapper with model-tier awareness."""

import json
import subprocess
from typing import List, Optional

from context_budget import SONNET, OPUS, TokenLedger, check_budget


class BaseAgent:
    MODEL: str = SONNET   # default; Opus agents override this

    def __init__(self, ledger: Optional[TokenLedger] = None) -> None:
        self.ledger = ledger

    def _run(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        system_prompt: Optional[str] = None,
        permission_mode: str = "default",
        budget_key: Optional[str] = None,
    ) -> str:
        """
        Invoke `claude --print` and return the final result text.
        budget_key: if set, checks this prompt against BUDGETS[budget_key].
        """
        if budget_key:
            check_budget(budget_key, prompt)

        tier = "opus" if self.MODEL == OPUS else "sonnet"
        print(f"    [{tier}] ", end="", flush=True)

        cmd = [
            "claude", "--print",
            "--model", self.MODEL,
            "--output-format", "stream-json",
            "--verbose",
            "--no-session-persistence",
        ]

        if tools:
            cmd += ["--tools", ",".join(tools)]
        else:
            cmd += ["--tools", ""]

        if system_prompt:
            cmd += ["--append-system-prompt", system_prompt]

        if permission_mode != "default":
            cmd += ["--permission-mode", permission_mode]

        proc = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
        )
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
                    raise RuntimeError(f"Claude error: {result}")

        proc.wait()
        print()

        if proc.returncode != 0 and not result:
            raise RuntimeError(
                f"Claude CLI rc={proc.returncode}: {proc.stderr.read()[:500]}"
            )

        if self.ledger and budget_key:
            self.ledger.record(budget_key, self.MODEL, prompt, result)

        return result
