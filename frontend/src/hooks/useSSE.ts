import { useState, useCallback, useRef } from "react";
import type { SSEMessage, ChatMessage } from "../types/chat";

export function useSSE() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const sendingRef = useRef(false);

  const sendMessage = useCallback(async (text: string) => {
    if (sendingRef.current) return;
    sendingRef.current = true;

    const userMsg: ChatMessage = {
      id: `u${Date.now()}`,
      role: "user",
      content: text,
    };
    const aiMsg: ChatMessage = {
      id: `a${Date.now()}`,
      role: "assistant",
      content: "",
      toolCalls: [],
      thinking: true,
    };

    setMessages((prev) => [...prev, userMsg, aiMsg]);
    setIsStreaming(true);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      const resp = await fetch("http://localhost:8000/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: text, thread_id: `web-${Date.now()}` }),
        signal: controller.signal,
      });

      const reader = resp.body?.getReader();
      if (!reader) { setIsStreaming(false); sendingRef.current = false; return; }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const msg: SSEMessage = JSON.parse(line.slice(6));
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (!last || last.role !== "assistant") return updated;

              switch (msg.type) {
                case "phase":
                  if (msg.phase === "thinking") {
                    last.thinking = true;
                    last.content = "";
                  }
                  break;
                case "tools":
                  last.toolCalls = (msg.tools || []).map((t: any) => ({
                    name: t.name,
                    label: t.label || "",
                    status: t.status as "running" | "done" | "error",
                  }));
                  break;
                case "token":
                  // 逐字追加
                  last.thinking = false;
                  last.content += (msg.content || "");
                  break;
                case "response":
                  // 兼容旧格式一次性响应
                  last.content = msg.content || "";
                  last.thinking = false;
                  break;
                case "hitl_required":
                  last.hitlPending = true;
                  last.thinking = false;
                  break;
                case "error":
                  last.content += `\n\n⚠️ 错误：${msg.content || ""}`;
                  last.thinking = false;
                  break;
              }
              return updated;
            });
          } catch { /* skip malformed */ }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) => {
          const u = [...prev];
          const last = u[u.length - 1];
          if (last?.role === "assistant") last.content += `\n\n⚠️ 请求失败：${err.message}`;
          return u;
        });
      }
    } finally {
      setIsStreaming(false);
      sendingRef.current = false;
    }
  }, []);

  const resumeAfterHitl = useCallback(async (_tid: string, approved: boolean) => {
    setMessages((prev) => {
      const u = [...prev];
      const last = u[u.length - 1];
      if (last?.role === "assistant") {
        last.hitlPending = false;
        last.content += approved ? "\n\n✅ 操作已确认执行。" : "\n\n⚠️ 操作已取消。";
      }
      return u;
    });
  }, []);

  return { messages, isStreaming, sendMessage, resumeAfterHitl };
}
