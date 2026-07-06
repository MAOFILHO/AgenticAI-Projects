"""Shared fault-injection seam, reused by every protocol client.

Fault mode is read fresh on every call (not cached), so it can be toggled at
runtime via env var or the Streamlit dashboard without restarting a server.
"""

import time

from shopsmart.config import get_fault_mode, get_timeout_s

VALID_MODES = {"none", "timeout", "error", "malformed", "refused"}


class ProtocolFault(Exception):
    """Raised for fault modes that should look like a hard failure (timeout/refused)."""

    def __init__(self, protocol: str, mode: str):
        self.protocol = protocol
        self.mode = mode
        super().__init__(f"[{protocol}] injected fault: {mode}")


class FaultInjector:
    def __init__(self, protocol: str):
        self.protocol = protocol

    def mode(self) -> str:
        mode = get_fault_mode(self.protocol)
        return mode if mode in VALID_MODES else "none"

    def maybe_inject_pre_call(self) -> None:
        """Call before making the actual protocol request."""
        mode = self.mode()
        if mode == "timeout":
            time.sleep(get_timeout_s(self.protocol) + 1)
            raise ProtocolFault(self.protocol, "timeout")
        if mode == "refused":
            raise ProtocolFault(self.protocol, "refused")

    def maybe_inject_post_call(self, payload: dict) -> dict:
        """Call after a successful protocol response, before returning it to the caller."""
        mode = self.mode()
        if mode == "error":
            return {"error": f"Injected error from {self.protocol} fault mode"}
        if mode == "malformed":
            return {"malformed": str(payload)[: max(1, len(str(payload)) // 3)]}
        return payload
