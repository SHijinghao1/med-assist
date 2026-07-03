import { useState, useRef, useEffect } from "react";
import { useSSE } from "./hooks/useSSE";
import "./App.css";

const TOOL_LABELS: Record<string, string> = {
  search_fault_code: "查询故障码",
  fault_code: "查询故障码",
  query_device_status: "查询设备状态",
  device_status: "查询设备状态",
  search_maintenance_logs: "搜索维修记录",
  maintenance_logs: "搜索维修记录",
  query_spare_parts: "查询备件库存",
  spare_parts: "查询备件库存",
  run_diagnostics: "执行诊断",
  diagnostics: "执行诊断",
  create_work_order: "创建工单",
  work_order: "创建工单",
};

const QUICK_QUESTIONS = [
  "背板报 E1023 怎么办",
  "背板电机怎么更换",
  "C臂旋转偏差校准",
  "背板电机备件库存",
];

/* ====== Markdown 渲染 ====== */
function renderMarkdown(text: string): string {
  const lines = text.split("\n");
  let html = "";
  let inList = false;

  for (const line of lines) {
    if (inList && !/^\d+\.\s/.test(line) && !line.startsWith("- ") && !line.startsWith("* ")) {
      html += "</ol>";
      inList = false;
    }
    if (line.startsWith("### ")) {
      if (inList) { html += "</ol>"; inList = false; }
      html += `<h3>${esc(line.slice(4))}</h3>`;
    } else if (line.startsWith("## ")) {
      if (inList) { html += "</ol>"; inList = false; }
      html += `<h2>${esc(line.slice(3))}</h2>`;
    } else if (/^\d+\.\s/.test(line)) {
      if (!inList) { html += "<ol>"; inList = true; }
      html += `<li>${inline(line.replace(/^\d+\.\s/, ""))}</li>`;
    } else if (line.startsWith("- ") || line.startsWith("* ")) {
      if (!inList) { html += "<ol>"; inList = true; }
      html += `<li>${inline(line.slice(2))}</li>`;
    } else if (line.trim() === "") {
      if (inList) { html += "</ol>"; inList = false; }
      html += "<br/>";
    } else {
      if (inList) { html += "</ol>"; inList = false; }
      html += `<p>${inline(line)}</p>`;
    }
  }
  if (inList) html += "</ol>";
  return html;
}
function esc(s: string) { return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;"); }
function inline(t: string) {
  return t
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/`(.+?)`/g, "<code>$1</code>");
}

/* ====== 子组件 ====== */
function Welcome({ onSend }: { onSend: (q: string) => void }) {
  return (
    <div className="welcome">
      <div className="welcome-icon">+</div>
      <h2>医疗设备运维助手</h2>
      <p>输入故障码、描述异常症状，或询问维修步骤</p>
      <div className="quick-btns">
        {QUICK_QUESTIONS.map((q) => (
          <button key={q} className="quick-btn" type="button" onClick={() => onSend(q)}>
            {q}
          </button>
        ))}
      </div>
    </div>
  );
}

function ThinkingBox() {
  return (
    <div className="thinking-box">
      <div className="thinking-spinner" />
      <span className="thinking-text">AI 正在分析您的问题...</span>
    </div>
  );
}

function ToolChips({ tools }: { tools?: { name: string; label: string; status: string }[] }) {
  if (!tools || tools.length === 0) return null;
  return (
    <div className="tool-chips">
      {tools.map((t, i) => (
        <span key={i} className={`tool-chip ${t.status}`}>
          <span className="tool-dot" />
          {t.label || TOOL_LABELS[t.name] || t.name}
        </span>
      ))}
    </div>
  );
}

function HitlBar({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="hitl-bar">
      <div className="hitl-bar-title">⚠️ 高危操作需要人工确认</div>
      <div className="hitl-actions">
        <button type="button" className="hitl-btn confirm" onClick={onConfirm}>确认执行</button>
        <button type="button" className="hitl-btn cancel" onClick={onCancel}>取消</button>
      </div>
    </div>
  );
}

/* ====== 主组件 ====== */
function App() {
  const { messages, isStreaming, sendMessage, resumeAfterHitl } = useSSE();
  const [input, setInput] = useState("");
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = () => {
    const text = input.trim();
    if (!text || isStreaming) return;
    sendMessage(text);
    setInput("");
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  /* 最后一条 AI 消息是否正在打字 */
  const lastAI = [...messages].reverse().find((m) => m.role === "assistant");
  const isTyping = isStreaming && lastAI?.thinking === false && !!lastAI?.content;

  return (
    <div className="app">
      {/* 头部 */}
      <header className="header">
        <div className="header-logo">+</div>
        <div>
          <h1>医疗设备运维助手</h1>
          <p>手术床 / C臂 · 故障诊断 · 维修指导 · 备件查询</p>
        </div>
      </header>

      {/* 聊天区 */}
      <div className="chat">
        {messages.length === 0 && <Welcome onSend={sendMessage} />}

        {messages.map((msg) => (
          <div key={msg.id} className={`msg-row ${msg.role}`}>
            {msg.role === "assistant" && <div className="msg-avatar">AI</div>}

            <div className="msg-body">
              {/* 工具调用 */}
              {msg.role === "assistant" && <ToolChips tools={msg.toolCalls} />}

              {/* 思考动画 */}
              {msg.thinking && !msg.content && <ThinkingBox />}

              {/* 消息气泡 */}
              <div className={`msg-bubble${isTyping && msg === lastAI ? " typing" : ""}`}>
                {msg.content ? (
                  <div dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }} />
                ) : !msg.thinking && msg.role === "assistant" ? (
                  <span className="no-reply">暂无回复</span>
                ) : null}
              </div>

              {/* HITL 确认栏 */}
              {msg.hitlPending && (
                <HitlBar
                  onConfirm={() => resumeAfterHitl("web-recent", true)}
                  onCancel={() => resumeAfterHitl("web-recent", false)}
                />
              )}
            </div>

            {msg.role === "user" && <div className="msg-avatar">我</div>}
          </div>
        ))}

        <div ref={chatEndRef} />
      </div>

      {/* 输入区 */}
      <div className="input-area">
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="输入故障描述，如：背板报 E1023 怎么办..."
          disabled={isStreaming}
        />
        <button type="button" onClick={handleSend} disabled={isStreaming || !input.trim()}>
          {isStreaming ? "思考中" : "发送"}
        </button>
      </div>
    </div>
  );
}

export default App;
