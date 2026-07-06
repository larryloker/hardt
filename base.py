"""Base class for in-process (native) MCP servers.

RECONSTRUCTED 2026-07-06: the original `mcp_servers/base.py` was NOT present in
the uploaded tree (no .py source and no .pyc anywhere), yet every native server
in mcp_servers/*.py does `from .base import BaseMCPServer`. This minimal base is
rebuilt to exactly satisfy the contract that mcp_client.NativeMCPServer relies on:

  - each public, non-underscore method of a server is a callable "tool"
    (NativeMCPServer.start introspects them; the method named `call` is excluded);
  - NativeMCPServer.call_tool does `resp = impl.call(tool, arguments)` and then
    reads `resp.success`, `resp.result`, `resp.error`.

If FXJEFE later supplies the original base.py, replace this file with it.
"""
from typing import Any, Dict, Optional


class ToolResponse:
    """Result envelope consumed by mcp_client.NativeMCPServer.call_tool."""
    __slots__ = ("success", "result", "error")

    def __init__(self, success: bool, result: Any = None, error: Optional[str] = None):
        self.success = success
        self.result = result
        self.error = error


class BaseMCPServer:
    """Minimal native MCP server base: dispatch a tool name to a bound method."""

    #: subclasses may set a human name; not required by the client
    name: str = ""

    def call(self, tool: str, arguments: Optional[Dict[str, Any]] = None) -> ToolResponse:
        arguments = arguments or {}
        if not isinstance(tool, str) or tool.startswith("_") or tool == "call":
            return ToolResponse(False, error=f"invalid tool name: {tool!r}")
        method = getattr(self, tool, None)
        if not callable(method):
            return ToolResponse(False, error=f"unknown tool: {tool!r}")
        try:
            return ToolResponse(True, result=method(**arguments))
        except TypeError as e:
            return ToolResponse(False, error=f"bad arguments for {tool!r}: {e}")
        except Exception as e:  # tools surface their own failures as errors, never crash the host
            return ToolResponse(False, error=f"{type(e).__name__}: {e}")
