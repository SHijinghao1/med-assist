#!/usr/bin/env python3
"""RAGAS 评估脚本 — 生成 baseline 报告"""
import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluation.test_cases import GROUND_TRUTH, EXPANDED_QUERIES
from evaluation.ragas_runner import run_full_evaluation, compare_runs

REPORT_DIR = Path(__file__).resolve().parent / "reports"
REPORT_DIR.mkdir(exist_ok=True)


def main():
    print("=" * 60)
    print("  Med-Assist RAGAS Evaluation")
    print("=" * 60)
    print()

    # 1. 跑评估
    print(f"[1] Running evaluation on {len(GROUND_TRUTH)} ground truth cases...")
    result = run_full_evaluation(GROUND_TRUTH)
    print(f"    Engine: {result.get('engine', 'unknown')}")
    print(f"    Faithfulness:      {result['faithfulness']:.3f}")
    print(f"    Context Relevancy: {result['context_relevancy']:.3f}")
    print(f"    Answer Relevancy:  {result['answer_relevancy']:.3f}")
    print()

    # 2. 保存基线
    report_path = REPORT_DIR / f"baseline_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump({
            "timestamp": datetime.now().isoformat(),
            "engine": result.get("engine", "unknown"),
            "test_cases": len(GROUND_TRUTH),
            "expanded_queries": len(EXPANDED_QUERIES),
            "scores": {
                "faithfulness": result["faithfulness"],
                "context_relevancy": result["context_relevancy"],
                "answer_relevancy": result["answer_relevancy"],
            },
        }, f, ensure_ascii=False, indent=2)
    print(f"[2] Baseline saved to: {report_path}")

    # 3. 检查历史报告（如果有）做对比
    existing = sorted(REPORT_DIR.glob("baseline_*.json"))
    if len(existing) >= 2:
        with open(existing[-2], "r") as f:
            prev = json.load(f)
        print()
        print("[3] Comparison with previous run:")
        print(compare_runs(prev["scores"], {
            "faithfulness": result["faithfulness"],
            "context_relevancy": result["context_relevancy"],
            "answer_relevancy": result["answer_relevancy"],
        }))

    print()
    print("=" * 60)
    print(f"  Test cases: {len(GROUND_TRUTH)} ground truth + {len(EXPANDED_QUERIES)} expanded")
    print(f"  Report: {report_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
