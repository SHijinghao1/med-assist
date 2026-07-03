# -*- coding: utf-8 -*-
"""End-to-end test - invoke graph directly"""
import asyncio
import sys
import traceback
sys.path.insert(0, ".")

async def main():
    from utils.logging import setup_logging
    setup_logging()

    from db.database import init_db, async_session
    from db.seed import seed_all
    from agent.supervisor import build_supervisor_graph
    from rag.retriever import HybridRetriever
    from main import llm_with_fallback
    from agent.state import AgentState
    from langchain_core.messages import HumanMessage
    from config import CHROMA_PERSIST_DIR, CHROMA_COLLECTION

    print("1. Init DB...")
    await init_db()
    async with async_session() as db:
        await seed_all(db)
    print("   OK")

    print("2. Init Chroma (may fail offline)...")
    collection = None
    try:
        import chromadb
        client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
        collection = client.get_or_create_collection(name=CHROMA_COLLECTION, metadata={"hnsw:space": "cosine"})
        print("   OK")
    except Exception as e:
        print(f"   SKIPPED: {e}")

    print("3. Init Retriever...")
    async with async_session() as db:
        retriever = HybridRetriever(db, collection)
    print("   OK")

    print("4. Build graph...")
    graph = build_supervisor_graph(
        db_session_factory=async_session,
        retriever=retriever,
        llm_call=llm_with_fallback,
    )
    print("   OK")

    print("5. Test LLM...")
    try:
        resp = await llm_with_fallback("Test")
        print(f"   LLM response length: {len(resp)}")
    except Exception as e:
        print(f"   LLM FAILED: {e}")
        traceback.print_exc()
        return

    print("6. Invoke graph with 'E1023'...")
    initial_state: AgentState = {
        "messages": [HumanMessage(content="E1023")],
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
    config = {"configurable": {"thread_id": "test-e2e"}}

    try:
        final = await graph.ainvoke(initial_state, config)
        response = final.get("final_response", "") if final else ""
        print(f"   Response length: {len(response)}")
        print(f"   Preview: {response[:300]}")
        if response:
            print("   >> E2E PASSED <<")
        else:
            print("   >> NO RESPONSE <<")
    except Exception as e:
        print(f"   GRAPH FAILED: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
