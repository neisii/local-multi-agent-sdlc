"""Base agent: drives the Claude CLI via subprocess (stream-json output)."""

import json
import subprocess
from typing import List, Optional


class BaseAgent:
    MODEL = "claude-opus-4-6"

    def _run(
        self,
        prompt: str,
        tools: Optional[List[str]] = None,
        cwd: Optional[str] = None,
        system_prompt: Optional[str] = None,
        permission_mode: str = "default",
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

        return result
