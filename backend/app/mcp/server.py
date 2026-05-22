"""
FitAgent MCP Server — minimal JSON-RPC 2.0 stdio transport (Phase 3B Step 1).

WHY manual protocol instead of mcp SDK:
  The mcp SDK has strict pydantic version requirements that conflict with
  the project's existing dependencies. A manual implementation of MCP's
  JSON-RPC 2.0 over stdio is ~200 lines and fully compliant with the spec.

WHY stdio transport:
  stdio is the standard MCP transport for Claude Desktop integration.
  No port conflicts, no auth needed — the parent process handles discovery.

Startup:
  python -m app.mcp.server

Protocol flow:
  1. Client → {"jsonrpc":"2.0","method":"initialize",...}
  2. Server → {"jsonrpc":"2.0","result":{"capabilities":{...}},...}
  3. Client → {"jsonrpc":"2.0","method":"notifications/initialized",...}
  4. Client → {"jsonrpc":"2.0","method":"tools/list",...}
  5. Server → {"jsonrpc":"2.0","result":{"tools":[...]},...}
  6. Client → {"jsonrpc":"2.0","method":"tools/call","params":{"name":"generate_training_plan","arguments":{...}},...}
  7. Server → {"jsonrpc":"2.0","result":{"content":[{"type":"text","text":"..."}]},...}
"""

import sys
import json
import asyncio
import logging
from typing import Any

# NOTE: Run as `python -m app.mcp.server` from the backend/ directory.
# The backend/ directory must be on sys.path (it is when using -m).

from app.mcp.tools import list_tools, call_tool
from app.mcp.resources import list_resources, read_resource
from app.mcp.prompts import list_prompts, get_prompt

logging.basicConfig(level=logging.INFO, format="[MCP] %(message)s")
logger = logging.getLogger("fitagent.mcp")

SERVER_NAME = "FitAgent MCP Server"
SERVER_VERSION = "0.1.0"


# =========================================================================
# MCP Protocol handlers
# =========================================================================


def handle_initialize(params: dict) -> dict:
    """
    Handle the MCP 'initialize' request.
    Return server capabilities: we support tools (no resources/prompts yet).
    """
    logger.info(f"Initialize from client: {params.get('clientInfo', {}).get('name', 'unknown')}")
    return {
        "protocolVersion": "2024-11-05",
        "capabilities": {
            "tools": {},     # Phase 3B Step 1-2: action execution
            "resources": {},  # Phase 3B Step 3: read-only data access
            "prompts": {},    # Phase 3B Step 4: workflow templates
        },
        "serverInfo": {
            "name": SERVER_NAME,
            "version": SERVER_VERSION,
        },
    }


def handle_tools_list(params: dict) -> dict:
    """Handle the MCP 'tools/list' request. Return all registered tools."""
    tools = list_tools()
    logger.info(f"Tools list requested: {len(tools)} tools")
    return {"tools": tools}


async def handle_tools_call(params: dict) -> dict:
    """
    Handle the MCP 'tools/call' request.
    Route to the appropriate tool handler based on tool name.
    """
    tool_name = params.get("name", "")
    arguments = params.get("arguments", {})
    logger.info(f"Tool call: {tool_name}")

    result = await call_tool(tool_name, arguments)

    # MCP spec: tool result is a list of content blocks
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(result, ensure_ascii=False, default=str),
            }
        ],
        "isError": not result.get("success", False),
    }


# =========================================================================
# MCP Resources handlers (Phase 3B Step 3)
# =========================================================================


def handle_resources_list(params: dict) -> dict:
    """Handle the MCP 'resources/list' request."""
    resources = list_resources()
    logger.info(f"Resources list requested: {len(resources)} resources")
    return {"resources": resources}


async def handle_resources_read(params: dict) -> dict:
    """
    Handle the MCP 'resources/read' request.

    Reads a resource by URI and returns the content as MCP content blocks.
    """
    uri = params.get("uri", "")
    logger.info(f"Resource read: {uri}")

    result = await read_resource(uri)

    return {
        "contents": [
            {
                "uri": uri,
                "mimeType": "application/json",
                "text": json.dumps(result, ensure_ascii=False, default=str),
            }
        ]
    }


# =========================================================================
# JSON-RPC 2.0 message loop
# =========================================================================


async def process_message(message: dict) -> dict | None:
    """
    Process a single JSON-RPC 2.0 message and return the response.

    Returns None for notifications (no response expected).
    """
    method = message.get("method", "")

    # MCP initialization
    if method == "initialize":
        return _rpc_response(message, handle_initialize(message.get("params", {})))

    # MCP tools
    elif method == "tools/list":
        return _rpc_response(message, handle_tools_list(message.get("params", {})))

    elif method == "tools/call":
        result = await handle_tools_call(message.get("params", {}))
        return _rpc_response(message, result)

    # MCP resources (Phase 3B Step 3)
    elif method == "resources/list":
        return _rpc_response(message, handle_resources_list(message.get("params", {})))

    elif method == "resources/read":
        result = await handle_resources_read(message.get("params", {}))
        return _rpc_response(message, result)

    # MCP prompts (Phase 3B Step 4)
    elif method == "prompts/list":
        return _rpc_response(message, {"prompts": list_prompts()})

    elif method == "prompts/get":
        params = message.get("params", {})
        result = get_prompt(params.get("name", ""), params.get("arguments", {}))
        if result["success"]:
            return _rpc_response(message, {
                "messages": result["prompt"]["messages"],
                "description": result["prompt"]["description"],
            })
        else:
            return _error_response(message, -32602, result["error"])

    # Notifications (no response)
    elif method.startswith("notifications/"):
        logger.info(f"Notification: {method}")
        return None

    # Ping
    elif method == "ping":
        return _rpc_response(message, {})

    # Unknown
    else:
        logger.warning(f"Unknown method: {method}")
        return _error_response(message, -32601, f"Method not found: {method}")


def _rpc_response(request: dict, result: dict) -> dict:
    """Build a JSON-RPC 2.0 success response."""
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "result": result,
    }


def _error_response(request: dict, code: int, message: str) -> dict:
    """Build a JSON-RPC 2.0 error response."""
    return {
        "jsonrpc": "2.0",
        "id": request.get("id"),
        "error": {"code": code, "message": message},
    }


# =========================================================================
# Stdio transport — main loop
# =========================================================================


async def main() -> None:
    """
    Run the MCP server over stdio.

    Reads JSON-RPC messages line-by-line from stdin.
    Writes JSON-RPC responses line-by-line to stdout.
    Stderr is reserved for logging.

    Each message is a single line of JSON (no newlines within messages).
    """
    logger.info(f"{SERVER_NAME} v{SERVER_VERSION} starting on stdio")

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    await asyncio.get_event_loop().connect_read_pipe(lambda: protocol, sys.stdin)

    writer_transport, writer_protocol = await asyncio.get_event_loop().connect_write_pipe(
        lambda: asyncio.streams.FlowControlMixin(), sys.stdout
    )

    buffer = ""
    while True:
        try:
            # Read a chunk from stdin
            chunk = await reader.read(4096)
            if not chunk:
                logger.info("Stdin closed, shutting down")
                break

            buffer += chunk.decode("utf-8")
            # Process complete lines
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    message = json.loads(line)
                except json.JSONDecodeError:
                    logger.error(f"Invalid JSON: {line[:100]}")
                    continue

                response = await process_message(message)
                if response is not None:
                    resp_line = json.dumps(response, ensure_ascii=False) + "\n"
                    sys.stdout.write(resp_line)
                    sys.stdout.flush()

        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")

    logger.info("MCP Server stopped")


if __name__ == "__main__":
    asyncio.run(main())
