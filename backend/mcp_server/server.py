"""MCP Server 入口 (stdio transport) — 对外暴露给 Claude Desktop 等外部 LLM"""
import asyncio
import json
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from mcp_server.schemas import TOOLS
from tools import execute_tool, TOOL_REGISTRY
from db.database import async_session

# 硬件工具不需要 db
NO_DB_TOOLS = {"get_device_state", "list_joints", "move_bed_joint", "move_carm_joint",
               "apply_bed_preset", "set_carm_mode", "emergency_stop", "reset_emergency"}

app = Server("med-assist-mcp")


@app.list_tools()
async def list_tools() -> list[Tool]:
    return [Tool(**schema) for schema in TOOLS]


@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name in NO_DB_TOOLS:
        result = await execute_tool(None, name, arguments)
    else:
        async with async_session() as db:
            result = await execute_tool(db, name, arguments)
    return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False, indent=2))]


async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())
