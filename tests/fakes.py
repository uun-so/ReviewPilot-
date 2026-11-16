from __future__ import annotations

from typing import Any, Callable


class FakeProvider:
    """Deterministic provider for tests; no network."""

    def __init__(self, handler: Callable[..., tuple[dict[str, Any], dict[str, int]]]):
        self.handler = handler
        self.calls: list[dict[str, Any]] = []

    def complete_json(self, **kwargs: Any) -> tuple[dict[str, Any], dict[str, int]]:
        self.calls.append(kwargs)
        return self.handler(**kwargs)
