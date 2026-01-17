# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server entrypoint.

Exposes GitHub and Supabase tools via Dedalus MCP framework.
Credentials provided by clients at runtime via token exchange.
"""

import os

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from db import db_tools, supabase
from gh import gh_tools, github
from smoke import smoke_tools

# Default to prod AS, override with DEDALUS_AS_URL env var
AS_URL = os.getenv("DEDALUS_AS_URL")

server = MCPServer(
    name="example-dedalus-mcp",
    connections=[github, supabase],
    http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    streamable_http_stateless=True,
    authorization_server=AS_URL,
)


async def main() -> None:
    """Start MCP server on port 8080."""
    server.collect(*smoke_tools, *gh_tools, *db_tools)
    await server.serve(port=8080)
