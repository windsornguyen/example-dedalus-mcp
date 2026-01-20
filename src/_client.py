# Copyright (c) 2026 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Sample MCP client demonstrating credential encryption and JIT token exchange.

Environment variables:
    DEDALUS_API_KEY: Your Dedalus API key (dsk_*)
    DEDALUS_API_URL: Product API base URL
    DEDALUS_AS_URL: Authorization server URL (for encryption key)
    GITHUB_TOKEN: GitHub personal access token
    SUPABASE_SECRET_KEY: Supabase service role key
    SUPABASE_URL: Supabase project URL
"""

import asyncio
import os

from dotenv import load_dotenv

load_dotenv()

from dedalus_labs import AsyncDedalus, DedalusRunner
from dedalus_mcp.auth import Connection, SecretKeys, SecretValues


class MissingEnvError(ValueError):
    """Required environment variable not set."""


def get_env(key: str) -> str:
    """Get required env var or raise."""
    val = os.getenv(key)
    if not val:
        raise MissingEnvError(key)
    return val


API_URL = get_env("DEDALUS_API_URL")
AS_URL = get_env("DEDALUS_AS_URL")
DEDALUS_API_KEY = os.getenv("DEDALUS_API_KEY")
SUPABASE_URL = get_env("SUPABASE_URL")

# Debug: print env vars
print("=== Environment ===")
print(f"  DEDALUS_API_URL: {API_URL}")
print(f"  DEDALUS_AS_URL: {AS_URL}")
print(f"  DEDALUS_API_KEY: {DEDALUS_API_KEY[:20]}..." if DEDALUS_API_KEY else "  DEDALUS_API_KEY: None")
print(f"  SUPABASE_URL: {SUPABASE_URL}")

# Connection: schema for a downstream service (name, required secrets, base URL).
github = Connection(
    name="github",
    secrets=SecretKeys(token="GITHUB_TOKEN"),  # noqa: S106, env var name, not actual secret
    base_url="https://api.github.com",
)

supabase = Connection(
    name="supabase",
    secrets=SecretKeys(key="SUPABASE_SECRET_KEY"),
    base_url=f"{SUPABASE_URL}/rest/v1",
    auth_header_name="apikey",  # Supabase uses 'apikey' header
    auth_header_format="{api_key}",  # raw value, no Bearer prefix
)

# SecretValues: binds actual credentials to a Connection schema.
# Encrypted client-side, decrypted in secure enclave at dispatch time.
github_secrets = SecretValues(github, token=os.getenv("GITHUB_TOKEN", ""))
supabase_secrets = SecretValues(supabase, key=os.getenv("SUPABASE_SECRET_KEY", ""))


async def run_with_runner() -> None:
    """Demo using DedalusRunner (handles multi-turn, aggregates results)."""
    client = AsyncDedalus(api_key=DEDALUS_API_KEY, base_url=API_URL, as_base_url=AS_URL)
    runner = DedalusRunner(client)

    result = await runner.run(
        input="Use db_select on 'mcp_repositories' table, columns 'slug,visibility', limit 5.",
        model="openai/gpt-4.1",
        mcp_servers=["windsor/example-dedalus-mcp"],
        credentials=[github_secrets, supabase_secrets],
    )

    print("=== Model Output ===")
    print(result.output)

    if result.mcp_results:
        print("\n=== MCP Tool Results ===")
        for r in result.mcp_results:
            print(f"  {r.tool_name} ({r.duration_ms}ms): {str(r.result)[:200]}")


async def run_raw() -> None:
    """Demo using raw client (single request, full control)."""
    client = AsyncDedalus(api_key=DEDALUS_API_KEY, base_url=API_URL, as_base_url=AS_URL)

    resp = await client.chat.completions.create(
        model="openai/gpt-4.1",
        messages=[
            {
                "role": "user",
                "content": "Use db_select on 'mcp_repositories' table, columns 'slug,visibility', limit 5.",
            }
        ],
        mcp_servers=["windsor/example-dedalus-mcp"],
        credentials=[github_secrets, supabase_secrets],
    )

    print("=== Model Output ===")
    print(resp.choices[0].message.content)

    if resp.mcp_tool_results:
        print("\n=== MCP Tool Results ===")
        for r in resp.mcp_tool_results:
            print(f"  {r.tool_name} ({r.duration_ms}ms): {str(r.result)[:200]}")


async def main() -> None:
    """Run both demo modes."""
    print("=" * 60)
    print("DedalusRunner")
    print("=" * 60)
    await run_with_runner()

    print("\n" + "=" * 60)
    print("Raw Client")
    print("=" * 60)
    await run_raw()


if __name__ == "__main__":
    asyncio.run(main())
