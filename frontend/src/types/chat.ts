export interface SSEMessage {
  type: "token" | "step" | "tool_start" | "tool_end" | "thinking_start" | "thinking_end" | "hitl_required" | "done" | "error";
  content?: string;
  name?: string;
  data?: any;
}

export interface ToolCall {
  name: string;
  label: string;
  status: "running" | "done" | "error";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  toolCalls?: ToolCall[];
  steps?: string[];
  thinking?: boolean;
  hitlPending?: boolean;
}
