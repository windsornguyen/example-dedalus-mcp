# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

from weather import weather_connections, weather_tools


# --- Server ------------------------------------------------------------------

server = MCPServer(
    name="open-meteo-mcp",
    connections=weather_connections,
    http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False),
)


async def main() -> None:
    server.collect(*weather_tools)
    await server.serve()
