"""Local smoke test for Admin API + OpenMCP AS token exchange.

This is intentionally NOT an LLM/chat test.
It proves the credential-handle pipeline works end-to-end:

1) Create a connection via Admin API using a user API key (dsk_*).
2) Exchange that API key for an audience-bound JWT via OpenMCP AS.
3) Pass the created connection handle via the generic `ext` form param.
4) Decode the JWT payload and assert `ddls:connections` contains the handle.
"""

from __future__ import annotations

import base64
import json
import os
import sys
from typing import Any

import httpx
from dotenv import load_dotenv

load_dotenv()


def _env(name: str, *, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing required env var: {name}")
    return value


def _base64url_random_bytes(byte_len: int) -> str:
    return base64.urlsafe_b64encode(os.urandom(byte_len)).decode().rstrip("=")


def _decode_jwt_payload(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) < 2:
        raise ValueError("Not a JWT (expected at least 2 dot-separated segments)")
    payload_b64 = parts[1]
    padding = "=" * (-len(payload_b64) % 4)
    payload_raw = base64.urlsafe_b64decode(payload_b64 + padding)
    return json.loads(payload_raw.decode())


def main() -> int:
    admin_url = _env("ADMIN_API_URL", default="http://localhost:8000").rstrip("/")
    as_url = _env("AS_URL", default="http://localhost:4444").rstrip("/")
    api_key = _env("DEDALUS_API_KEY")
    resource = os.getenv("MCP_RESOURCE", "http://127.0.0.1:9000/mcp")

    # Admin API enforces base64url + minimum length (~500 chars). Use random bytes.
    encrypted_credentials = _base64url_random_bytes(700)

    connection_name = os.getenv("CONNECTION_NAME", "github")

    with httpx.Client(timeout=10.0) as client:
        resp = client.post(
            f"{admin_url}/v1/connections/create",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "name": connection_name,
                "provider": connection_name,
                "backing_type": "api_key",
                "encrypted_credentials": encrypted_credentials,
            },
        )
        resp.raise_for_status()
        handle = resp.json().get("handle")
        if not handle:
            raise RuntimeError(f"Admin API did not return a handle: {resp.text}")

        token_resp = client.post(
            f"{as_url}/oauth2/token",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data={
                "grant_type": "urn:ietf:params:oauth:grant-type:token-exchange",
                "subject_token": api_key,
                "subject_token_type": "urn:ietf:params:oauth:token-type:api_key",
                "resource": resource,
                "ext": json.dumps({"connections": {connection_name: handle}}, separators=(",", ":"), sort_keys=True),
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json().get("access_token")
        if not access_token:
            raise RuntimeError(f"AS did not return access_token: {token_resp.text}")

    claims = _decode_jwt_payload(access_token)
    connections = claims.get("ddls:connections")

    print("ok")
    print(f"connection_handle={handle}")
    print(f"aud={claims.get('aud')}")
    print(f"ddls:connections={connections}")

    if claims.get("aud") != resource:
        print(f"FAIL: aud mismatch (expected {resource})", file=sys.stderr)
        return 2
    if not isinstance(connections, dict) or connections.get(connection_name) != handle:
        print(f"FAIL: ddls:connections[{connection_name}] != {handle}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

