import { useState, useRef, useEffect } from "react";
import { Send, StopCircle, Plus, Sparkles, User } from "lucide-react";
import { sendMessage, ChatMessage } from "../api";

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingContent]);

  // Auto-resize textarea
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [input]);

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setStreamingContent("");
    setIsStreaming(false);
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    if (streamingContent) {
      setMessages((prev) => [
        ...prev,
        {
          id: Date.now().toString(),
          role: "assistant",
          content: streamingContent + " [cancelled]",
          created_at: new Date().toISOString(),
        },
      ]);
      setStreamingContent("");
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: "user",
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsStreaming(true);
    setStreamingContent("");

    try {
      const data = await sendMessage(userMessage.content, conversationId || undefined, false);
      if (data.error) throw new Error(data.error);
      if (data.detail) throw new Error(JSON.stringify(data.detail));

      setConversationId(data.conversation_id);
      setMessages((prev) => [
        ...prev,
        {
          id: data.message.id,
          role: "assistant",
          content: data.message.content,
          created_at: data.message.created_at,
        },
      ]);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Unknown error";
      if (msg !== "AbortError") {
        setMessages((prev) => [
          ...prev,
          {
            id: (Date.now() + 1).toString(),
            role: "assistant",
            content: `⚠️ ${msg}`,
            created_at: new Date().toISOString(),
          },
        ]);
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const isEmpty = messages.length === 0 && !streamingContent;

  return (
    <div className="flex flex-col h-full bg-[#0d0f17]">

      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#252836] bg-[#161921]/80 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div>
            <h1 className="text-[14px] font-semibold text-slate-100">Chat</h1>
            <p className="text-[11px] text-slate-500 mt-0.5">
              {conversationId ? `Session · ${conversationId.slice(0, 8)}` : "New conversation"}
            </p>
          </div>
        </div>
        <button
          onClick={handleNewConversation}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#1c1f2e] border border-[#252836] hover:border-blue-500/40 hover:bg-blue-600/10 transition-all text-[12px] font-medium text-slate-400 hover:text-blue-400"
        >
          <Plus size={14} />
          New chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <EmptyState />
        ) : (
          <div className="max-w-2xl mx-auto px-4 py-6 space-y-5">
            {messages.map((msg) => (
              <MessageBubble key={msg.id} msg={msg} />
            ))}

            {/* Streaming content */}
            {isStreaming && streamingContent && (
              <div className="flex gap-3 animate-fade-up">
                <AiAvatar />
                <div className="flex-1 min-w-0">
                  <div className="bg-[#1c1f2e] border border-[#252836] rounded-2xl rounded-tl-sm px-4 py-3">
                    <p className="text-[13px] text-slate-200 whitespace-pre-wrap leading-relaxed">
                      {streamingContent}
                      <span className="inline-block w-0.5 h-3.5 bg-blue-400 animate-pulse ml-0.5 align-middle" />
                    </p>
                  </div>
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {isStreaming && !streamingContent && (
              <div className="flex gap-3 animate-fade-up">
                <AiAvatar />
                <div className="bg-[#1c1f2e] border border-[#252836] rounded-2xl rounded-tl-sm px-4 py-3.5 flex items-center gap-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 dot-1" />
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 dot-2" />
                  <span className="w-1.5 h-1.5 rounded-full bg-blue-400 dot-3" />
                </div>
              </div>
            )}

            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input area */}
      <div className="px-4 pb-4 pt-3 border-t border-[#252836] bg-[#0d0f17]">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-end gap-2 bg-[#161921] border border-[#252836] rounded-2xl px-3 py-2 focus-within:border-blue-500/50 transition-colors">
            <textarea
              ref={textareaRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message InferFlow… (Enter to send, Shift+Enter for newline)"
              rows={1}
              disabled={isStreaming}
              className="flex-1 bg-transparent text-[13px] text-slate-200 placeholder-slate-600 focus:outline-none py-1.5 leading-relaxed max-h-40 disabled:opacity-50"
            />
            {isStreaming ? (
              <button
                onClick={handleCancel}
                className="flex-shrink-0 w-8 h-8 mb-0.5 rounded-xl bg-red-600/20 border border-red-500/30 hover:bg-red-600/30 flex items-center justify-center text-red-400 transition-all"
              >
                <StopCircle size={15} />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!input.trim()}
                className="flex-shrink-0 w-8 h-8 mb-0.5 rounded-xl bg-blue-600 hover:bg-blue-500 flex items-center justify-center text-white transition-all disabled:opacity-30 disabled:cursor-not-allowed"
              >
                <Send size={13} />
              </button>
            )}
          </div>
          <p className="text-center text-[11px] text-slate-700 mt-2">
            Responses are logged with inference metadata · Gemini 2.5 Flash
          </p>
        </div>
      </div>
    </div>
  );
}

function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === "user";
  return (
    <div className={`flex gap-3 animate-fade-up ${isUser ? "flex-row-reverse" : ""}`}>
      {isUser ? <UserAvatar /> : <AiAvatar />}
      <div className={`flex-1 min-w-0 flex flex-col ${isUser ? "items-end" : "items-start"}`}>
        <div
          className={`max-w-[88%] px-4 py-3 rounded-2xl text-[13px] leading-relaxed whitespace-pre-wrap ${
            isUser
              ? "bg-gradient-to-br from-blue-600 to-blue-700 text-white rounded-tr-sm shadow-lg shadow-blue-900/30"
              : "bg-[#1c1f2e] border border-[#252836] text-slate-200 rounded-tl-sm"
          }`}
        >
          {msg.content}
        </div>
        <span className="text-[10px] text-slate-600 mt-1 px-1">
          {new Date(msg.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
        </span>
      </div>
    </div>
  );
}

function AiAvatar() {
  return (
    <div className="w-7 h-7 flex-shrink-0 rounded-xl bg-gradient-to-br from-violet-500 to-blue-600 flex items-center justify-center shadow-md shadow-blue-900/30 mt-0.5">
      <Sparkles size={13} className="text-white" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="w-7 h-7 flex-shrink-0 rounded-xl bg-[#1c1f2e] border border-[#2e3147] flex items-center justify-center mt-0.5">
      <User size={13} className="text-slate-400" />
    </div>
  );
}

function EmptyState() {
  const suggestions = [
    "Explain how transformer attention works",
    "Write a Python function to parse JSON",
    "What's the difference between RAG and fine-tuning?",
    "Help me debug this async race condition",
  ];
  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12 text-center">
      <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-blue-600 to-indigo-700 flex items-center justify-center shadow-xl shadow-blue-900/40 mb-5">
        <Sparkles size={26} className="text-white" />
      </div>
      <h2 className="text-lg font-semibold text-slate-200 mb-1">How can I help you?</h2>
      <p className="text-[13px] text-slate-500 mb-8 max-w-xs">
        Every message is logged with latency, tokens, and inference metadata.
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 w-full max-w-lg">
        {suggestions.map((s) => (
          <button
            key={s}
            className="text-left px-4 py-3 rounded-xl bg-[#161921] border border-[#252836] hover:border-blue-500/30 hover:bg-blue-600/5 transition-all text-[12px] text-slate-400 hover:text-slate-300"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  );
}
