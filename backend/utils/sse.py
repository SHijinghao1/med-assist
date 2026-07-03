"""SSE (Server-Sent Events) 流式响应工具"""
import json
from typing import AsyncIterator


EVENT_TYPE_MAP = {
    "on_chat_model_start": "thinking_start",
    "on_chat_model_stream": "token",
    "on_chat_model_end": "thinking_end",
    "on_tool_start": "tool_start",
    "on_tool_end": "tool_end",
    "on_human_input_required": "hitl_required",
    "on_custom_event": "custom",
}


def _summarize_output(output, max_len: int = 100):
    """截断 Tool 输出用于前端展示"""
    if isinstance(output, dict):
        s = json.dumps(output, ensure_ascii=False)
    else:
        s = str(output)
    return s[:max_len] + ("..." if len(s) > max_len else "")


async def sse_generator(agent_stream: AsyncIterator[dict]) -> AsyncIterator[str]:
    """
    将 LangGraph astream_events 转为 SSE 事件流。

    用法:
        @app.post("/chat")
        async def chat(request: ChatRequest):
            stream = graph.astream_events(...)
            return StreamingResponse(
                sse_generator(stream),
                media_type="text/event-stream"
            )
    """
    async for event in agent_stream:
        event_type = event.get("event", "")
        name = event.get("name", "")

        if event_type == "on_chat_model_start":
            yield f"data: {json.dumps({'type': 'thinking_start', 'name': name}, ensure_ascii=False)}\n\n"

        elif event_type == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

        elif event_type == "on_chat_model_end":
            yield f"data: {json.dumps({'type': 'thinking_end', 'name': name}, ensure_ascii=False)}\n\n"

        elif event_type == "on_tool_start":
            yield f"data: {json.dumps({'type': 'tool_start', 'name': name, 'input': event.get('data', {}).get('input')}, ensure_ascii=False)}\n\n"

        elif event_type == "on_tool_end":
            output = event.get("data", {}).get("output")
            yield f"data: {json.dumps({'type': 'tool_end', 'name': name, 'output_summary': _summarize_output(output)}, ensure_ascii=False)}\n\n"

        elif event_type == "on_human_input_required":
            yield f"data: {json.dumps({'type': 'hitl_required', 'data': event.get('data', {})}, ensure_ascii=False)}\n\n"

    yield f"data: {json.dumps({'type': 'done'})}\n\n"
