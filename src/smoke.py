# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Smoke test tools for validating MCP handshake.

These tools avoid ctx.dispatch() to test SDK serialization and
token exchange without requiring enclave dispatch.
"""

from pydantic.dataclasses import dataclass

from dedalus_mcp import tool


@dataclass(frozen=True)
class PingResult:
    """Smoke ping response."""

    ok: bool = True
    message: str = "pong"


@tool(description="Smoke test ping (no enclave dispatch required)")
async def smoke_ping(message: str = "pong") -> PingResult:
    """Simple ping for testing MCP connection.

    Args:
        message: Message to echo back (default "pong")

    Returns:
        PingResult with ok=True and echoed message

    """
    return PingResult(message=message)


smoke_tools = [smoke_ping]
