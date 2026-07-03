"""Self-Reflection 自纠错"""
import json
from agent.state import AgentState
from utils.logging import log

REFLECTION_PROMPT = """审查以下诊断结果，四个维度评分(1-5):
1. 数据支撑性: 每个结论是否引用了具体数据?
2. 来源准确性: 引用的手册章节/故障码是否正确?
3. 步骤完整性: 排查步骤是否有遗漏?
4. 安全性: 高危操作是否已标记?

评分标准:
总分 ≥ 16 → PASS | 12-15 → WARN | <12 → FAIL

诊断输出:
{diagnosis}

请输出 JSON (不要额外文本):
{{"scores": {{"data_support": int, "source_accuracy": int, "step_completeness": int, "safety": int}},
  "total": int, "verdict": "PASS"|"WARN"|"FAIL",
  "issues": ["问题描述"], "corrected": "修正版(如果是FAIL)"}}"""


async def reflect_and_refine(state: AgentState, llm_call, on_token=None, max_retries: int = 1) -> AgentState:
    """Self-Reflection 节点: 审查 + 修正"""
    diagnosis = state.get("final_response", "")

    if not diagnosis or len(diagnosis) < 20:
        state["reflection_verdict"] = "SKIP"
        return state

    for attempt in range(max_retries + 1):
        prompt = REFLECTION_PROMPT.format(diagnosis=diagnosis)
        raw = await llm_call(prompt, on_token)

        try:
            # 提取 JSON
            if "```json" in raw:
                raw = raw.split("```json")[1].split("```")[0]
            elif "```" in raw:
                raw = raw.split("```")[1].split("```")[0]
            result = json.loads(raw)
        except (json.JSONDecodeError, IndexError):
            log.warning("reflection.parse_error", attempt=attempt)
            state["reflection_verdict"] = "PARSE_ERROR"
            return state

        verdict = result.get("verdict", "PASS")
        scores = result.get("scores", {})
        issues = result.get("issues", [])

        state["reflection_scores"] = scores

        if verdict == "PASS":
            log.info("reflection.pass", scores=scores)
            state["reflection_verdict"] = "PASS"
            break

        elif verdict == "WARN":
            state["final_response"] = diagnosis + "\n\n---\n⚠️ 审查备注: " + "; ".join(issues)
            state["reflection_verdict"] = "WARN"
            log.info("reflection.warn", issues=issues)
            break

        else:  # FAIL
            corrected = result.get("corrected")
            if attempt == 0 and corrected:
                diagnosis = corrected
                state["final_response"] = corrected
                log.info("reflection.fail_corrected", scores=scores)
            else:
                state["final_response"] = diagnosis + "\n\n---\n⚠️⚠️ 无法自动修正，建议人工复核。"
                state["reflection_verdict"] = "FAIL_UNFIXABLE"
                log.warning("reflection.fail_unfixable", scores=scores)
                break

    return state
