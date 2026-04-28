"""Sniffer sidecar supervisor — STUB.

The real implementation will spawn vendor/inmarsat-sniffer/build/inmarsat-sniffer
as a subprocess, parse its JSON UDP feed, and expose decode events. Until that
binary is vendored, every method raises NotImplementedError.

See docs/archive/merge_plan.html for the full integration plan.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional


_NOT_VENDORED_MSG = (
    "inmarsat-sniffer not vendored yet — see docs/archive/merge_plan.html"
)


@dataclass
class SnifferStatus:
    pid: Optional[int] = None
    running: bool = False
    last_decode_at: Optional[float] = None
    decode_count: int = 0


class SnifferSidecar:
    """Manages the inmarsat-sniffer C binary as a subprocess sidecar.

    Stub: every method raises NotImplementedError until vendor/inmarsat-sniffer
    is populated and built.
    """

    def __init__(self, config: dict):
        self.config = config

    def start(self) -> None:
        raise NotImplementedError(_NOT_VENDORED_MSG)

    def stop(self) -> None:
        raise NotImplementedError(_NOT_VENDORED_MSG)

    def status(self) -> SnifferStatus:
        raise NotImplementedError(_NOT_VENDORED_MSG)

    def is_running(self) -> bool:
        raise NotImplementedError(_NOT_VENDORED_MSG)
