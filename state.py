"""Shared state object passed between all agents."""

import json
from dataclasses import dataclass, asdict


@dataclass
class SDLCState:
    prd: str = ""
    spec: str = ""
    architecture: str = ""
    code: str = ""
    audit: str = ""
    iteration: int = 0

    def to_dict(self) -> dict:
        return asdict(self)

    def save(self, path: str = "state.json") -> None:
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load(cls, path: str) -> "SDLCState":
        with open(path) as f:
            return cls(**json.load(f))
