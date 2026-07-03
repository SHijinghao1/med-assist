"""RAGAS 评估运行器（轻量版——无 ragas 依赖时用简单指标）"""
import json
import math
from typing import List
from utils.logging import log


class SimpleEvaluator:
    """简单评估器：不依赖 ragas 库，用关键词匹配做基础评估"""

    def evaluate(self, test_cases: List[dict]) -> dict:
        """运行评估，返回三个指标"""
        scores = {"faithfulness": [], "context_relevancy": [], "answer_relevancy": []}

        for tc in test_cases:
            answer = tc.get("answer", "")
            question = tc.get("question", "")
            contexts = tc.get("contexts", [])

            # 1. Faithfulness: 回答中的关键词在 context 中的比率
            faith = self._keyword_coverage(answer, " ".join(contexts))
            scores["faithfulness"].append(faith)

            # 2. Context Relevancy: context 中的关键词在 question 中的比率
            ctx_rel = self._keyword_coverage(" ".join(contexts), question)
            scores["context_relevancy"].append(ctx_rel)

            # 3. Answer Relevancy: 回答和问题的关键词重叠率
            ans_rel = self._keyword_coverage(answer, question)
            scores["answer_relevancy"].append(ans_rel)

        return {
            "faithfulness": round(self._mean(scores["faithfulness"]), 3),
            "context_relevancy": round(self._mean(scores["context_relevancy"]), 3),
            "answer_relevancy": round(self._mean(scores["answer_relevancy"]), 3),
            "total_cases": len(test_cases),
        }

    @staticmethod
    def _keyword_coverage(source: str, target: str) -> float:
        """source 中的关键词有多少在 target 中出现"""
        src_words = set(source.lower().split())
        tgt_words = set(target.lower().split())
        if not src_words:
            return 0.0
        intersection = src_words & tgt_words
        return len(intersection) / len(src_words)

    @staticmethod
    def _mean(values: List[float]) -> float:
        return sum(values) / len(values) if values else 0.0


def run_full_evaluation(test_cases: List[dict]) -> dict:
    """运行完整评估（优先用 ragas，不可用时用简单评估器）"""
    try:
        from ragas import evaluate as ragas_evaluate
        from ragas.metrics import faithfulness, context_relevancy, answer_relevancy
        from datasets import Dataset

        dataset = Dataset.from_list(test_cases)
        result = ragas_evaluate(dataset, metrics=[
            faithfulness(),
            context_relevancy(),
            answer_relevancy(),
        ])
        return {
            "faithfulness": float(result.get("faithfulness", 0)),
            "context_relevancy": float(result.get("context_relevancy", 0)),
            "answer_relevancy": float(result.get("answer_relevancy", 0)),
            "total_cases": len(test_cases),
            "engine": "ragas",
        }
    except ImportError:
        log.info("evaluation.using_simple_evaluator")
        evaluator = SimpleEvaluator()
        result = evaluator.evaluate(test_cases)
        result["engine"] = "simple"
        return result


def compare_runs(before: dict, after: dict) -> str:
    """对比两次评估结果"""
    lines = ["## RAGAS Evaluation Comparison", ""]
    lines.append("| Metric | Before | After | Delta |")
    lines.append("|--------|--------|-------|-------|")
    for metric in ["faithfulness", "context_relevancy", "answer_relevancy"]:
        b = before.get(metric, 0)
        a = after.get(metric, 0)
        delta = a - b
        emoji = "+" if delta > 0.05 else ("-" if delta < -0.05 else "=")
        lines.append(f"| {metric} | {b:.3f} | {a:.3f} | {emoji} {delta:+.3f} |")
    return "\n".join(lines)
