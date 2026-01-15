# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""MCP server entrypoint.

Exposes GitHub and Supabase tools via Dedalus MCP framework.
Credentials provided by clients at runtime via token exchange.
"""

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from db import db_tools, supabase
from gh import gh_tools, github
from smoke import smoke_tools

server = MCPServer(
    name="example-dedalus-mcp",
    connections=[github, supabase],
    http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
    streamable_http_stateless=True,
    authorization_server="https://preview.as.dedaluslabs.ai",
)


async def main() -> None:
    """Start MCP server on port 8080."""
    server.collect(*smoke_tools, *gh_tools, *db_tools)
    await server.serve(port=8080)
