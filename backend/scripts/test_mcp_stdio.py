#!/usr/bin/env python
"""
FitAgent MCP protocol verification — validates all JSON-RPC handlers.

Usage:
  cd backend
  python scripts/test_mcp_stdio.py

This verifies the MCP protocol logic by calling server.process_message()
directly (same handlers Claude Desktop uses via stdio). It does NOT spawn
a subprocess (which has known asyncio+Windows compatibility issues).

For actual Claude Desktop integration, the subprocess is managed by
Claude Desktop itself, which handles OS-level pipe creation correctly.
"""

import asyncio
import json
import sys
import os

# Ensure backend is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.mcp.server import process_message

REQUESTS = [
    # 1. Initialize
    {
        "name": "initialize",
        "msg": {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}},
        "checks": [
            ("result.protocolVersion", lambda r: r["result"].get("protocolVersion") == "2024-11-05"),
            ("result.capabilities.tools", lambda r: "tools" in r["result"]["capabilities"]),
            ("result.capabilities.resources", lambda r: "resources" in r["result"]["capabilities"]),
            ("result.capabilities.prompts", lambda r: "prompts" in r["result"]["capabilities"]),
            ("result.serverInfo.name", lambda r: r["result"]["serverInfo"]["name"] == "FitAgent MCP Server"),
        ],
    },
    # 2. tools/list
    {
        "name": "tools/list",
        "msg": {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        "checks": [
            ("result.tools count=4", lambda r: len(r["result"]["tools"]) == 4),
            ("has generate_training_plan", lambda r: any(t["name"] == "generate_training_plan" for t in r["result"]["tools"])),
            ("has search_fitness_knowledge", lambda r: any(t["name"] == "search_fitness_knowledge" for t in r["result"]["tools"])),
        ],
    },
    # 3. tools/call — generate_training_plan
    {
        "name": "tools/call generate_training_plan",
        "msg": {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {
                "name": "generate_training_plan",
                "arguments": {
                    "goal": "fat_loss", "height_cm": 175, "weight_kg": 80,
                    "training_location": "gym", "weekly_days": 4, "experience_level": "intermediate",
                },
            },
        },
        "checks": [
            ("result.content exists", lambda r: "content" in r["result"]),
            ("content[0].type=text", lambda r: r["result"]["content"][0]["type"] == "text"),
            ("plan in text", lambda r: "weekly_schedule" in r["result"]["content"][0]["text"]),
        ],
    },
    # 4. resources/list
    {
        "name": "resources/list",
        "msg": {"jsonrpc": "2.0", "id": 4, "method": "resources/list", "params": {}},
        "checks": [
            ("result.resources count=4", lambda r: len(r["result"]["resources"]) == 4),
            ("has active-plan", lambda r: any(x["uri"] == "fitness://active-plan" for x in r["result"]["resources"])),
            ("has monthly-summary", lambda r: any(x["uri"] == "fitness://monthly-summary" for x in r["result"]["resources"])),
        ],
    },
    # 5. resources/read
    {
        "name": "resources/read active-plan",
        "msg": {
            "jsonrpc": "2.0", "id": 5, "method": "resources/read",
            "params": {"uri": "fitness://active-plan?user_id=test123"},
        },
        "checks": [
            ("result.contents exists", lambda r: "contents" in r["result"]),
        ],
    },
    # 6. prompts/list
    {
        "name": "prompts/list",
        "msg": {"jsonrpc": "2.0", "id": 6, "method": "prompts/list", "params": {}},
        "checks": [
            ("result.prompts count=5", lambda r: len(r["result"]["prompts"]) == 5),
            ("has create-fitness-plan", lambda r: any(p["name"] == "create-fitness-plan" for p in r["result"]["prompts"])),
        ],
    },
    # 7. prompts/get
    {
        "name": "prompts/get weekly-review",
        "msg": {
            "jsonrpc": "2.0", "id": 7, "method": "prompts/get",
            "params": {"name": "weekly-review"},
        },
        "checks": [
            ("result.messages exists", lambda r: "messages" in r["result"]),
            ("system+user messages", lambda r: len(r["result"]["messages"]) == 2),
        ],
    },
    # 8. Error handling — unknown tool
    {
        "name": "tools/call unknown → error",
        "msg": {
            "jsonrpc": "2.0", "id": 8, "method": "tools/call",
            "params": {"name": "nonexistent_tool", "arguments": {}},
        },
        "checks": [
            ("result.isError=true", lambda r: r["result"].get("isError") == True),
        ],
    },
    # 9. Error handling — unknown method
    {
        "name": "unknown method → error",
        "msg": {"jsonrpc": "2.0", "id": 9, "method": "unknown/method", "params": {}},
        "checks": [
            ("error.code=-32601", lambda r: r["error"]["code"] == -32601),
        ],
    },
]


async def run_test():
    passed = 0
    failed = 0

    print("=" * 60)
    print("FitAgent MCP Protocol Verification")
    print(f"Testing {len(REQUESTS)} JSON-RPC scenarios")
    print("=" * 60)

    for test in REQUESTS:
        try:
            resp = await process_message(test["msg"])
            if resp is None:
                print(f"\n[{test['name']}] FAIL: No response (notification?)")
                failed += 1
                continue

            # Run checks
            all_ok = True
            for check_name, check_fn in test["checks"]:
                try:
                    if not check_fn(resp):
                        print(f"\n[{test['name']}] FAIL: {check_name}")
                        all_ok = False
                except Exception as e:
                    print(f"\n[{test['name']}] FAIL: {check_name} — {e}")
                    all_ok = False

            if all_ok:
                print(f"[{test['name']}] PASS")
                passed += 1

        except Exception as e:
            print(f"\n[{test['name']}] FAIL: {e}")
            failed += 1

    print("\n" + "=" * 60)
    print(f"Results: {passed} passed, {failed} failed out of {len(REQUESTS)}")
    print("=" * 60)

    if passed == len(REQUESTS):
        print("\nAll MCP protocol tests passed.")
        print("FitAgent MCP Server is ready for Claude Desktop integration.")
        print("\nNext step:")
        print("  1. Copy docs/claude-desktop-config.example.json")
        print("  2. Replace paths and user ID")
        print("  3. Restart Claude Desktop")
        print("  4. Type 'help me create a workout plan' in Claude Desktop")
    else:
        print(f"\n{failed} test(s) failed. Review the output above.")

    return failed == 0


def main():
    success = asyncio.run(run_test())
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
