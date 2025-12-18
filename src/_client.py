# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample MCP client demonstrating MCP secrets + JIT token exchange.

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (dsk_*)
    GITHUB_TOKEN: GitHub personal access token
    SUPABASE_SECRET_KEY: Supabase service role key
    SUPABASE_URL: Supabase project URL
    DEDALUS_API_URL: Product API base URL (default: http://localhost:8080)
    DEDALUS_AS_URL: OpenMCP AS base URL used to fetch the encryption public key
                   (default: http://localhost:4444)
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

# Server framework provides Connection/SecretKeys/SecretValues definitions
from dedalus_mcp.auth import Connection, SecretKeys, SecretValues
from dedalus_mcp import MCPServer
from dedalus_mcp.server import TransportSecuritySettings

# SDK provides client-side encryption + request serialization
from dedalus_labs import AsyncDedalus, DedalusRunner

# --- Configuration ------------------------------------------------------------

# Dev environment URLs
API_URL = os.getenv("DEDALUS_API_URL")

if not API_URL:
    msg = "DEDALUS_API_URL is not set"
    raise ValueError(msg)

AS_URL = os.getenv("DEDALUS_AS_URL")
if not AS_URL:
    msg = "DEDALUS_AS_URL is not set"
    raise ValueError(msg)

# Auth
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")


# --- Connection Definitions ---------------------------------------------------
# These define WHAT secrets are needed (schema).
# Typically imported from your MCP server package (e.g., from server import github, supabase)

github = Connection(
    name="github",
    secrets=SecretKeys(token="GITHUB_TOKEN"),
    base_url="https://api.github.com",
)

SUPABASE_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_URL:
    msg = "SUPABASE_URL is not set"
    raise ValueError(msg)

supabase = Connection(
    name="supabase",
    secrets=SecretKeys(key="SUPABASE_SECRET_KEY"),
    base_url=f"{SUPABASE_URL}/rest/v1",
    auth_header_name="apikey",
    auth_header_format="{api_key}",
)


# --- Secret Bindings ----------------------------------------------------------
# These provide ACTUAL values for the secrets.

github_secrets = SecretValues(github, token=os.getenv("GITHUB_TOKEN", ""))
supabase_secrets = SecretValues(supabase, key=os.getenv("SUPABASE_SECRET_KEY", ""))


# --- MCP Server Definitions ---------------------------------------------------

srv1 = MCPServer(
    name="windsor/example-dedalus-mcp",
    connections=[github, supabase],
    http_security=TransportSecuritySettings(enable_dns_rebinding_protection=False)
)

# Optional local override: treat this MCPServer instance as a direct URL server.
# This is only for local smoke testing (avoids marketplace lookup for `slug`).
_local_mcp_url = os.getenv("MCP_SERVER_URL")
if _local_mcp_url:
    srv1._serving_url = _local_mcp_url  # type: ignore[attr-defined]

# --- Main ---------------------------------------------------------------------


async def main_with_runner() -> None:
    """Example using DedalusRunner (handles multi-turn, aggregates mcp_results)."""
    client = AsyncDedalus(
        api_key=DEDALUS_API_KEY,
        base_url=API_URL,
        as_base_url=AS_URL,
    )

    runner = DedalusRunner(client)
    result = await runner.run(
        input="Use the GitHub tool to list all repositories.",
        model="openai/gpt-4.1",
        mcp_servers=[srv1],
        credentials=[github_secrets, supabase_secrets],
    )

    print("=== [DedalusRunner] Model Output ===")
    print(result.output)

    # MCP results parsed into MCPToolResult dataclasses
    if result.mcp_results:
        print("\n=== [DedalusRunner] MCP Tool Executions ===")
        for mcp in result.mcp_results:
            print(f"  Tool: {mcp.tool_name}")
            print(f"  Server: {mcp.server_name}")
            print(f"  Arguments: {mcp.arguments}")
            print(f"  Duration: {mcp.duration_ms}ms")
            print(f"  Is Error: {mcp.is_error}")
            result_str = str(mcp.result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"  Result: {result_str}")
            print()


async def main_with_raw_client() -> None:
    """Example using raw AsyncDedalus client (single request, raw response)."""
    client = AsyncDedalus(
        api_key=DEDALUS_API_KEY,
        base_url=API_URL,
        as_base_url=AS_URL,
    )

    # Raw client call - mcp_tool_executions is on the ChatCompletion response
    response = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[{"role": "user", "content": "Use the GitHub tool to list all repositories."}],
        mcp_servers=[srv1],
        credentials=[github_secrets, supabase_secrets],
    )

    print("=== [Raw Client] Model Output ===")
    print(response.choices[0].message.content)

    # Access mcp_tool_executions directly on the response
    if response.mcp_tool_executions:
        print("\n=== [Raw Client] MCP Tool Executions ===")
        for mcp in response.mcp_tool_executions:
            print(f"  Tool: {mcp.tool_name}")
            print(f"  Server: {mcp.server_name}")
            print(f"  Arguments: {mcp.arguments}")
            print(f"  Duration: {mcp.duration_ms}ms")
            print(f"  Is Error: {mcp.is_error}")
            result_str = str(mcp.result)
            if len(result_str) > 200:
                result_str = result_str[:200] + "..."
            print(f"  Result: {result_str}")
            print()


async def main() -> None:
    """Run both examples."""
    print("=" * 60)
    print("EXAMPLE 1: Using DedalusRunner")
    print("=" * 60)
    await main_with_runner()

    print("\n" + "=" * 60)
    print("EXAMPLE 2: Using Raw Client")
    print("=" * 60)
    await main_with_raw_client()


if __name__ == "__main__":
    asyncio.run(main())
