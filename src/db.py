# Copyright (c) 2025 Dedalus Labs, Inc. and its contributors
# SPDX-License-Identifier: MIT

"""Supabase CRUD tools via REST API.

Credentials (URL and API key) provided by client via token exchange.
No server-side environment variables required.
"""

from typing import Any
from urllib.parse import quote

from pydantic import Field
from pydantic.dataclasses import dataclass

from dedalus_mcp import HttpMethod, HttpRequest, get_context, tool
from dedalus_mcp.auth import Connection, SecretKeys

supabase = Connection(
    name="supabase",
    secrets=SecretKeys(key="SUPABASE_SECRET_KEY"),
    auth_header_name="apikey",
    auth_header_format="{api_key}",
)


@dataclass(frozen=True)
class DbResult:
    """Database operation result."""

    success: bool
    data: list[dict[str, Any]] = Field(default_factory=list)
    count: int | None = None
    error: str | None = None


@dataclass(frozen=True)
class DbSingle:
    """Single row result."""

    success: bool
    data: dict[str, Any] | None = None
    error: str | None = None


def _enc(q: str) -> str:
    """URL-encode preserving PostgREST operators (=, &, etc)."""
    return quote(q, safe="=&,.*-_~:")


def _hdrs(prefer: str | None = None) -> dict[str, str]:
    """Build Supabase headers. apikey injected by framework."""
    h = {"Content-Type": "application/json"}
    if prefer:
        h["Prefer"] = prefer
    return h


def _to_list(body: Any) -> list[dict[str, Any]]:
    """Normalize response body to list."""
    if isinstance(body, list):
        return body
    return [body] if body else []


@tool(description="Select rows from a Supabase table with optional filters, ordering, and pagination")
async def db_select(
    table: str,
    columns: str = "*",
    filters: str | None = None,
    order: str | None = None,
    limit: int | None = None,
    offset: int | None = None,
) -> DbResult:
    """Query rows from a table.

    Args:
        table: Table name
        columns: Columns to select (default "*")
        filters: PostgREST filter string (e.g. "status=eq.active", "age=gt.18")
        order: Order by column (e.g. "created_at.desc")
        limit: Max rows to return
        offset: Rows to skip

    Returns:
        DbResult with rows in data field

    """
    ctx = get_context()
    q = f"select={columns}"
    if filters:
        q += f"&{filters}"
    if order:
        q += f"&order={order}"
    if limit:
        q += f"&limit={limit}"
    if offset:
        q += f"&offset={offset}"

    req = HttpRequest(method=HttpMethod.GET, path=f"/{table}?{_enc(q)}", headers=_hdrs("count=exact"))
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        data = _to_list(resp.response.body)
        return DbResult(success=True, data=data, count=len(data))
    return DbResult(success=False, error=resp.error.message if resp.error else "Query failed")


@tool(description="Insert one or more rows into a Supabase table")
async def db_insert(table: str, rows: list[dict[str, Any]], *, return_data: bool = True) -> DbResult:
    """Insert rows into a table.

    Args:
        table: Table name
        rows: List of row objects to insert
        return_data: Return inserted rows (default True)

    Returns:
        DbResult with inserted rows if return_data=True

    """
    ctx = get_context()
    prefer = "return=representation" if return_data else "return=minimal"
    req = HttpRequest(method=HttpMethod.POST, path=f"/{table}", headers=_hdrs(prefer), body=rows)
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        return DbResult(success=True, data=_to_list(resp.response.body), count=len(rows))
    return DbResult(success=False, error=resp.error.message if resp.error else "Insert failed")


@tool(description="Update rows in a Supabase table matching the specified filters")
async def db_update(table: str, updates: dict[str, Any], filters: str, *, return_data: bool = True) -> DbResult:
    """Update rows matching filters.

    Args:
        table: Table name
        updates: Fields to update
        filters: PostgREST filter (required, e.g. "id=eq.123")
        return_data: Return updated rows (default True)

    Returns:
        DbResult with updated rows if return_data=True

    """
    ctx = get_context()
    prefer = "return=representation" if return_data else "return=minimal"
    req = HttpRequest(method=HttpMethod.PATCH, path=f"/{table}?{_enc(filters)}", headers=_hdrs(prefer), body=updates)
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        data = _to_list(resp.response.body)
        return DbResult(success=True, data=data, count=len(data))
    return DbResult(success=False, error=resp.error.message if resp.error else "Update failed")


@tool(description="Delete rows from a Supabase table matching the specified filters")
async def db_delete(table: str, filters: str, *, return_data: bool = False) -> DbResult:
    """Delete rows matching filters.

    Args:
        table: Table name
        filters: PostgREST filter (required, e.g. "id=eq.123")
        return_data: Return deleted rows (default False)

    Returns:
        DbResult with deleted rows if return_data=True

    """
    ctx = get_context()
    prefer = "return=representation" if return_data else "return=minimal"
    req = HttpRequest(method=HttpMethod.DELETE, path=f"/{table}?{_enc(filters)}", headers=_hdrs(prefer))
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        return DbResult(success=True, data=_to_list(resp.response.body))
    return DbResult(success=False, error=resp.error.message if resp.error else "Delete failed")


@tool(description="Upsert rows into a Supabase table (insert or update on conflict)")
async def db_upsert(
    table: str, rows: list[dict[str, Any]], *, on_conflict: str = "id", return_data: bool = True
) -> DbResult:
    """Upsert rows (insert or update on conflict).

    Args:
        table: Table name
        rows: List of row objects
        on_conflict: Column for conflict resolution (default "id")
        return_data: Return upserted rows (default True)

    Returns:
        DbResult with upserted rows if return_data=True

    """
    ctx = get_context()
    prefer = ("return=representation" if return_data else "return=minimal") + ",resolution=merge-duplicates"
    req = HttpRequest(
        method=HttpMethod.POST, path=f"/{table}?on_conflict={on_conflict}", headers=_hdrs(prefer), body=rows
    )
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        return DbResult(success=True, data=_to_list(resp.response.body), count=len(rows))
    return DbResult(success=False, error=resp.error.message if resp.error else "Upsert failed")


@tool(description="Get a single row by primary key from a Supabase table")
async def db_get_by_id(table: str, id_column: str, id_value: str | int, columns: str = "*") -> DbSingle:
    """Fetch a single row by ID.

    Args:
        table: Table name
        id_column: Primary key column name
        id_value: Primary key value
        columns: Columns to select (default "*")

    Returns:
        DbSingle with row data or error if not found

    """
    ctx = get_context()
    q = f"select={columns}&{id_column}=eq.{id_value}"
    req = HttpRequest(method=HttpMethod.GET, path=f"/{table}?{_enc(q)}", headers=_hdrs("return=representation"))
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        body = resp.response.body
        if isinstance(body, list) and body:
            return DbSingle(success=True, data=body[0])
        if isinstance(body, dict):
            return DbSingle(success=True, data=body)
        return DbSingle(success=False, error="Not found")
    return DbSingle(success=False, error=resp.error.message if resp.error else "Query failed")


@tool(description="Call a Supabase RPC (stored procedure/function)")
async def db_rpc(function_name: str, params: dict[str, Any] | None = None) -> DbResult:
    """Call a stored procedure.

    Args:
        function_name: Name of the RPC function
        params: Parameters to pass to the function

    Returns:
        DbResult with function return value in data field

    """
    ctx = get_context()
    req = HttpRequest(method=HttpMethod.POST, path=f"/rpc/{function_name}", headers=_hdrs(), body=params or {})
    resp = await ctx.dispatch("supabase", req)

    if resp.success:
        return DbResult(success=True, data=_to_list(resp.response.body))
    return DbResult(success=False, error=resp.error.message if resp.error else "RPC failed")


db_tools = [db_select, db_insert, db_update, db_delete, db_upsert, db_get_by_id, db_rpc]
