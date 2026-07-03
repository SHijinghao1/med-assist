"""FastAPI 入口 + SSE 端点 — 串联所有组件"""
import json
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from config import BASE_DIR, DATA_DIR, CHROMA_PERSIST_DIR, CHROMA_COLLECTION
from db.database import init_db, get_db, async_session
from db.seed import seed_all
from observability.middleware import TraceMiddleware
from utils.logging import setup_logging, log
from utils.sse import sse_generator

from rag.retriever import HybridRetriever
from rag.semantic_cache import semantic_cache
from agent.supervisor import build_supervisor_graph
from agent.state import AgentState
from agent.human_loop import needs_human_approval, handle_approval
from safety.input_validators import validate_input
from resilience.fallback import FallbackChain
from resilience.circuit_breaker import CircuitBreaker
from langchain_core.messages import HumanMessage, AIMessage

# ── 全局组件 ──
_supervisor_graph = None
_retriever = None
_chroma_collection = None
_llm_fallback = None


def _strip_json_blocks(text: str) -> str:
    """裁掉末尾的 ```json ... ``` 代码块（reflection 泄漏）"""
    import re
    return re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL).strip()


# ── LLM 调用封装 ──

async def _call_deepseek(prompt: str) -> str:
    """调用 DeepSeek API（非流式，兼容旧代码）"""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-your-key-here":
        raise RuntimeError("DeepSeek API key not configured")
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={"model": DEEPSEEK_MODEL, "messages": [{"role":"user","content":prompt}], "temperature":0.3, "max_tokens":2000},
        )
        return resp.json()["choices"][0]["message"]["content"]


async def _call_deepseek_stream(prompt: str, on_token):
    """流式调用 DeepSeek——每收到 token 就回调"""
    import httpx
    from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, DEEPSEEK_MODEL
    if not DEEPSEEK_API_KEY or DEEPSEEK_API_KEY == "sk-your-key-here":
        raise RuntimeError("DeepSeek API key not configured")
    async with httpx.AsyncClient(timeout=60.0) as client:
        async with client.stream(
            "POST", f"{DEEPSEEK_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {DEEPSEEK_API_KEY}"},
            json={"model": DEEPSEEK_MODEL, "messages": [{"role":"user","content":prompt}], "temperature":0.3, "max_tokens":2000, "stream": True},
        ) as resp:
            async for line in resp.aiter_lines():
                if line.startswith("data: ") and line != "data: [DONE]":
                    import json as _json
                    chunk = _json.loads(line[6:])
                    delta = chunk.get("choices", [{}])[0].get("delta", {})
                    content = delta.get("content", "")
                    if content:
                        await on_token(content)


async def _call_qwen(prompt: str) -> str:
    import httpx
    from config import QWEN_API_KEY, QWEN_BASE_URL, QWEN_MODEL
    if not QWEN_API_KEY or QWEN_API_KEY == "sk-your-key-here":
        raise RuntimeError("Qwen API key not configured")
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{QWEN_BASE_URL}/chat/completions",
            headers={"Authorization": f"Bearer {QWEN_API_KEY}"},
            json={"model": QWEN_MODEL, "messages": [{"role":"user","content":prompt}], "temperature":0.3, "max_tokens":2000})
        return resp.json()["choices"][0]["message"]["content"]


async def _mock_llm_response(prompt: str) -> str:
    """Mock LLM 响应（无 API key 时使用）"""
    if "E1023" in prompt or "背板" in prompt:
        return """## 诊断结果

**故障码 E1023 — 背板电机过载保护**

### 最可能原因（排序）
1. **导轨润滑不足**（概率 70%）——历史 3 次 E1023 故障均为润滑问题导致机械卡滞
2. **电机轴承磨损**（概率 20%）——长期运行后轴承间隙增大
3. **控制板电流传感器漂移**（概率 10%）

### 排查步骤
1. 断开电源，手动转动背板检查是否有卡滞感
2. 检查导轨润滑脂状态——若发黑或干涸需更换
3. 用万用表测量电机三相绕组电阻（标准 2.1Ω ±10%）
4. 如电阻正常，检测控制板电流采样电路

### 所需备件
- **MTR-BK-001** 背板驱动电机总成（库存 5 个）
- **GRS-BK-001** 导轨专用润滑脂（库存 20 个）

### ⚠️ 如需执行电机强制复位
请确认后执行，此操作不可逆。"""
    elif "维修" in prompt or "更换" in prompt:
        return """## 维修指导

### 背板电机更换步骤
1. **断电** —— 拔掉设备电源插头，等待 5 分钟电容放电
2. 拆除背板外壳（6 颗 M5 内六角螺丝）
3. 断开电机接线端子（拍照记录线序）
4. 松掉 4 颗固定螺栓，取下旧电机
5. 安装新电机，力矩 8N·m
6. 按照片恢复接线
7. 通电测试：空载运行 3 个循环
8. 校准背板零位传感器

⚠️ 第 5 步需扭矩扳手，第 8 步需校准工具。"""
    return f"关于「{prompt[:50]}...」的诊断结果：\n\n需要更多信息才能给出准确诊断。请提供设备类型、故障码或具体症状。"


async def llm_with_fallback(prompt: str, on_token=None) -> str:
    """
    LLM 调用——支持流式回调。
    如果 on_token 不为 None，走流式（每收到 token 就回调）；
    否则走非流式，返回完整结果。
    """
    from config import DEEPSEEK_API_KEY

    if on_token and DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "sk-your-key-here":
        # 流式调用 DeepSeek
        full = []
        async def collect(t): full.append(t); await on_token(t)
        try:
            await _call_deepseek_stream(prompt, collect)
            return "".join(full)
        except Exception:
            pass

    # 非流式
    if DEEPSEEK_API_KEY and DEEPSEEK_API_KEY != "sk-your-key-here":
        try:
            return await _call_deepseek(prompt)
        except Exception:
            pass

    return await _mock_llm_response(prompt)


# ── 应用生命周期 ──

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _supervisor_graph, _retriever, _chroma_collection

    setup_logging()
    log.info("app.starting")

    await init_db()

    # 种子数据
    async with async_session() as db:
        await seed_all(db)

    # Chroma 初始化
    try:
        import chromadb
        chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        _chroma_collection = chroma_client.get_or_create_collection(
            name=CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        log.info("chroma.ready", path=CHROMA_PERSIST_DIR)

        # 摄入知识库文档
        from rag.ingest_docs import ingest_all_manuals
        doc_count = await ingest_all_manuals(_chroma_collection)
        log.info("chroma.ingested", documents=doc_count)
    except Exception as e:
        log.warning("chroma.unavailable", error=str(e))

    # Retriever
    async with async_session() as db:
        _retriever = HybridRetriever(db, _chroma_collection)

    # Supervisor Graph
    _supervisor_graph = build_supervisor_graph(
        db_session_factory=async_session,
        retriever=_retriever,
        llm_call=llm_with_fallback,
    )
    log.info("supervisor.ready")

    yield

    log.info("app.stopping")


app = FastAPI(
    title="智能医疗设备运维助手",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(TraceMiddleware)


# ── 请求/响应模型 ──

class ChatRequest(BaseModel):
    message: str
    thread_id: str = "default"
    device_type: Optional[str] = None
    device_id: Optional[str] = None


class ResumeRequest(BaseModel):
    thread_id: str
    approved: bool


# ── 路由 ──

@app.get("/health")
async def health():
    return {"ok": True, "service": "med-assist"}


@app.post("/chat")
async def chat(request: ChatRequest):
    """主对话端点——SSE 流式输出"""
    if _supervisor_graph is None:
        raise HTTPException(503, "Agent 未就绪")

    # 输入校验
    guard_result = await validate_input(request.message)
    if not guard_result["passed"]:
        raise HTTPException(422, guard_result.get("reason", "输入被拦截"))

    # 语义缓存
    cached = await semantic_cache.lookup(request.message)
    if cached:

        async def cached_stream():
            yield f"data: {json.dumps({'type': 'token', 'content': cached}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return StreamingResponse(cached_stream(), media_type="text/event-stream",
                                 headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})

    # 构建初始 State
    initial_state: AgentState = {
        "messages": [HumanMessage(content=request.message)],
        "active_expert": None,
        "fault_code_hit": None,
        "bm25_docs": [],
        "semantic_docs": [],
        "tool_results": {},
        "input_guard_passed": True,
        "output_guard_result": None,
        "pending_approval": None,
        "approval_granted": False,
        "reflection_scores": None,
        "reflection_verdict": None,
        "cache_hit": False,
        "fallback_level": 0,
        "final_response": None,
    }

    token_queue: asyncio.Queue = asyncio.Queue()
    config = {"configurable": {"thread_id": request.thread_id, "token_queue": token_queue}}

    # SSE 流式输出
    async def stream():
        try:
            # Phase 1: 思考中
            yield f"data: {json.dumps({'type': 'phase', 'phase': 'thinking'})}\n\n"

            # 后台运行 Agent 图
            graph_task = asyncio.create_task(
                _supervisor_graph.ainvoke(initial_state, config)
            )

            # 实时读取 token 队列并推给前端
            token_count = 0
            while not graph_task.done() or not token_queue.empty():
                try:
                    token = await asyncio.wait_for(token_queue.get(), timeout=0.05)
                    yield f"data: {json.dumps({'type': 'token', 'content': token})}\n\n"
                    token_count += 1
                except asyncio.TimeoutError:
                    pass

            final_state = await graph_task

            if final_state:
                # 工具调用信息
                tool_results = final_state.get("tool_results", {})
                if tool_results:
                    tools_info = [{"name": n, "status": "done" if r else "error"} for n, r in tool_results.items()]
                    yield f"data: {json.dumps({'type': 'tools', 'tools': tools_info})}\n\n"

                pending = final_state.get("pending_approval")
                if pending:
                    yield f"data: {json.dumps({'type': 'hitl_required', 'operation': pending})}\n\n"

                # 非流式兜底：如果没有 token 推送过，发送完整响应
                response = final_state.get("final_response", "")
                if token_count == 0 and response:
                    clean = _strip_json_blocks(response)
                    yield f"data: {json.dumps({'type': 'response', 'content': clean})}\n\n"

        except Exception as e:
            log.error("stream.error", error=str(e))
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/chat/resume")
async def resume_chat(request: ResumeRequest):
    """HITL 恢复端点"""
    if _supervisor_graph is None:
        raise HTTPException(503, "Agent 未就绪")

    config = {"configurable": {"thread_id": request.thread_id}}
    current_state = await _supervisor_graph.aget_state(config)

    if not current_state or not current_state.values:
        raise HTTPException(404, "会话未找到")

    state = current_state.values
    state["approval_granted"] = request.approved
    state["pending_approval"] = None

    if request.approved:
        state["messages"].append(
            AIMessage(content="✅ 用户已确认高危操作，继续执行...")
        )
    else:
        state["final_response"] = "⚠️ 用户取消了高危操作。"

    # 继续执行后续节点
    async def stream():
        try:
            async for event in _supervisor_graph.astream_events(None, config, version="v2"):
                event_type = event.get("event", "")
                if event_type == "on_chat_model_stream":
                    chunk = event.get("data", {}).get("chunk")
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield f"data: {json.dumps({'type': 'token', 'content': chunk.content}, ensure_ascii=False)}\n\n"

            final_state = await _supervisor_graph.aget_state(config)
            if final_state and final_state.values:
                response = final_state.values.get("final_response", "")
                if response:
                    yield f"data: {json.dumps({'type': 'token', 'content': response}, ensure_ascii=False)}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

        yield f"data: {json.dumps({'type': 'done'})}\n\n"

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── 评估端点 ──
@app.get("/evaluation")
async def run_evaluation():
    from evaluation.test_cases import GROUND_TRUTH
    from evaluation.ragas_runner import run_full_evaluation
    return run_full_evaluation(GROUND_TRUTH)


# ── MCP 工具调用端点 ──
@app.get("/tools")
async def list_tools():
    from tools import TOOL_REGISTRY
    return {
        name: {"description": info["description"], "dangerous": info["dangerous"]}
        for name, info in TOOL_REGISTRY.items()
    }


# ── IOBS 兼容 API（供 iobs-unified-app 3D 可视化前端使用）──
from tools.surgical_device import (
    _device_state, BED_JOINTS, CARM_JOINTS, BED_PRESETS,
    get_device_state as _get_dev_state, move_bed_joint as _move_bed,
    move_carm_joint as _move_carm, apply_bed_preset as _apply_preset,
    set_carm_mode as _set_mode, emergency_stop as _estop,
    reset_emergency as _reset_estop,
)


@app.get("/iobs-api/health")
async def iobs_health():
    return {"ok": True}


@app.get("/iobs-api/get_pos")
async def iobs_get_pos(version: str = "1.0"):
    bed = _device_state["bed"]
    carm = _device_state["cArm"]
    return {
        "version": version,
        "error": "",
        "pos": {
            "surgical_bed": {
                "position": [0, 0, 0], "rotation": [0, 0, 0],
                "joints": {k: v for k, v in bed.items()},
                "stateName": "", "progress": 0, "device": "surgical_bed", "error": "",
            },
            "c_arm": {
                "position": [0, 0, 0], "rotation": [0, 0, 0],
                "joints": {k: v for k, v in carm.items()},
                "stateName": "", "progress": 0, "device": "c_arm", "error": "",
            },
        },
    }


@app.get("/iobs-api/get_status")
async def iobs_get_status(version: str = "1.0"):
    return {"status": {pid: {"name": p["name"], "state": p["state"]} for pid, p in BED_PRESETS.items()}}


@app.get("/iobs-api/get_c_arm_mode")
async def iobs_get_carm_mode(version: str = "1.0"):
    return {"mode": _device_state["cArmMode"], "auto": 0}


@app.get("/iobs-api/set_joint_move")
async def iobs_set_joint(version: str = "1.0", device: str = "", joint: str = "", speed: float = 5.0,
                         type: str = "target", value: float = 0.0):
    if _device_state["emergencyStopped"]:
        return {"ok": False, "error": "Emergency stopped"}
    if device == "surgical_bed":
        args = {"joint": joint, "target_value": value} if type == "target" else {"joint": joint, "delta": value}
        return await _move_bed(args)
    elif device == "c_arm":
        args = {"joint": joint, "target_value": value} if type == "target" else {"joint": joint, "delta": value}
        return await _move_carm(args)
    return {"ok": False, "error": f"Unknown device: {device}"}


@app.get("/iobs-api/set_preset")
async def iobs_set_preset(version: str = "1.0", preset_id: str = ""):
    return await _apply_preset({"preset_id": preset_id})


@app.get("/iobs-api/set_c_arm_mode")
async def iobs_set_carm(version: str = "1.0", mode: int = 0):
    return await _set_mode({"mode": mode})


@app.post("/iobs-api/set_stop")
async def iobs_set_stop(version: str = "1.0", action: str = "stop"):
    if action == "stop":
        return await _estop()
    else:
        return await _reset_estop()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
