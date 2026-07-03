"""三级检索器: SQL 精确 → BM25 关键词 → 语义向量 + RRF 融合 + Reranker 精排"""
from collections import defaultdict
from typing import List, Optional

import jieba
from rank_bm25 import BM25Okapi
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.fault_code import FaultCode
from models.maintenance_log import MaintenanceLog
from rag.embedder import embedder
from utils.logging import log


class HybridRetriever:
    """三级检索器"""

    def __init__(self, db: AsyncSession, chroma_collection=None):
        self.db = db
        self.chroma = chroma_collection
        self._bm25: Optional[BM25Okapi] = None
        self._bm25_docs: List[dict] = []

    # ── L1: SQL 精确匹配 ──

    async def search_fault_code(self, code: str) -> Optional[dict]:
        """SQL 精确匹配故障码，O(1)"""
        stmt = select(FaultCode).where(FaultCode.code == code.upper())
        result = await self.db.execute(stmt)
        fc = result.scalar_one_or_none()
        if fc:
            log.info("retrieval.l1_sql_hit", code=code)
            return fc.to_dict()
        log.info("retrieval.l1_sql_miss", code=code)
        return None

    # ── L2: BM25 全文搜索 ──

    async def _ensure_bm25_index(self):
        """懒加载 BM25 索引"""
        if self._bm25 is not None:
            return

        stmt = select(MaintenanceLog).order_by(MaintenanceLog.created_at.desc()).limit(1000)
        result = await self.db.execute(stmt)
        logs = result.scalars().all()

        self._bm25_docs = [log.to_dict() for log in logs]
        corpus = []
        for doc in self._bm25_docs:
            tokens = list(jieba.cut(f"{doc['fault_code']} {doc['description']} {doc['solution']}"))
            corpus.append(tokens)

        self._bm25 = BM25Okapi(corpus)

    async def search_bm25(self, query: str, k: int = 10) -> List[dict]:
        """BM25 关键词检索"""
        await self._ensure_bm25_index()
        if not self._bm25:
            return []

        tokens = list(jieba.cut(query))
        scores = self._bm25.get_scores(tokens)
        # 取 Top-K
        indexed = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results = []
        for idx, score in indexed[:k]:
            if score > 0:
                doc = self._bm25_docs[idx].copy()
                doc["_bm25_score"] = float(score)
                results.append(doc)

        log.info("retrieval.l2_bm25", query=query[:50], hits=len(results))
        return results

    # ── L3: 语义向量检索 ──

    async def search_semantic(self, query: str, top_k: int = 10) -> List[dict]:
        """语义向量检索 + Reranker 精排"""
        if self.chroma is None:
            log.warning("retrieval.l3_chroma_unavailable")
            return []

        try:
            query_embedding = await embedder.embed_query(query)
        except Exception:
            log.warning("retrieval.l3_embedding_failed", query=query[:50])
            return []

        # Chroma 粗排
        chroma_results = self.chroma.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k * 2, 20),
        )

        if not chroma_results.get("ids") or not chroma_results["ids"][0]:
            return []

        docs = []
        for i, doc_id in enumerate(chroma_results["ids"][0]):
            docs.append({
                "id": doc_id,
                "content": chroma_results["documents"][0][i] if chroma_results.get("documents") else "",
                "source": chroma_results["metadatas"][0][i].get("source", "") if chroma_results.get("metadatas") else "",
                "_cosine_score": 1.0 - chroma_results["distances"][0][i] if chroma_results.get("distances") else 0.0,
            })

        # Reranker 精排 (Cross-Encoder)
        if len(docs) > 3:
            docs = await self._rerank(query, docs, top_k)

        log.info("retrieval.l3_semantic", query=query[:50], hits=len(docs))
        return docs[:top_k]

    async def _rerank(self, query: str, docs: List[dict], top_k: int) -> List[dict]:
        """Cross-Encoder 精排"""
        try:
            from sentence_transformers import CrossEncoder
            import asyncio
            model = CrossEncoder("BAAI/bge-reranker-v2-m3")
            pairs = [(query, doc["content"]) for doc in docs]
            loop = asyncio.get_event_loop()
            scores = await loop.run_in_executor(None, lambda: model.predict(pairs))
            for doc, score in zip(docs, scores):
                doc["_rerank_score"] = float(score)
            docs.sort(key=lambda d: d.get("_rerank_score", 0), reverse=True)
        except ImportError:
            pass  # 没有 Reranker 就用 cosine 分数
        return docs

    # ── 混合检索: BM25 + 语义 RRF 融合 ──

    async def hybrid_search(self, query: str, top_k: int = 5) -> List[dict]:
        """BM25 + 语义向量 RRF 融合检索"""
        # 并行执行两路检索
        import asyncio
        bm25_task = asyncio.create_task(self.search_bm25(query, k=10))
        semantic_task = asyncio.create_task(self.search_semantic(query, top_k=10))

        bm25_results = await bm25_task
        semantic_results = await semantic_task

        # RRF 融合
        fused = self._rrf_fusion(bm25_results, semantic_results, k=60)

        log.info(
            "retrieval.hybrid",
            query=query[:50],
            bm25_hits=len(bm25_results),
            semantic_hits=len(semantic_results),
            fused_hits=len(fused),
        )
        return fused[:top_k]

    def _rrf_fusion(
        self,
        ranking_a: List[dict],
        ranking_b: List[dict],
        k: int = 60,
    ) -> List[dict]:
        """RRF (Reciprocal Rank Fusion) 融合两路排序结果"""
        scores = defaultdict(float)
        doc_map = {}

        for rank, doc in enumerate(ranking_a):
            key = doc.get("id", doc.get("content", str(rank)))
            scores[key] += 1.0 / (k + rank + 1)
            doc_map[key] = doc

        for rank, doc in enumerate(ranking_b):
            key = doc.get("id", doc.get("content", str(rank)))
            scores[key] += 1.0 / (k + rank + 1)
            doc_map[key] = doc

        ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        return [doc_map[key] for key, _ in ranked if key in doc_map]
