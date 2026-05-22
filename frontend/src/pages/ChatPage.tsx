import { useState, useRef, useEffect } from 'react';
import { Send, StopCircle, Plus } from 'lucide-react';
import { sendMessage, ChatMessage } from '../api';

export default function ChatPage() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState('');
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleNewConversation = () => {
    setMessages([]);
    setConversationId(null);
    setStreamingContent('');
    setIsStreaming(false);
  };

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    if (streamingContent) {
      setMessages(prev => [...prev, { id: Date.now().toString(), role: 'assistant', content: streamingContent + ' [cancelled]', created_at: new Date().toISOString() }]);
      setStreamingContent('');
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isStreaming) return;

    const userMessage: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: input.trim(),
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    try {
      const response = await sendMessage(userMessage.content, conversationId || undefined, true);

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let fullContent = '';

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const text = decoder.decode(value, { stream: true });
          const lines = text.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.content) {
                  fullContent += data.content;
                  setStreamingContent(fullContent);
                }
                if (data.done) {
                  setConversationId(data.conversation_id);
                }
                if (data.error) {
                  throw new Error(data.error);
                }
              } catch (e) {
                // Skip malformed JSON lines
              }
            }
          }
        }
      }

      if (fullContent) {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: fullContent,
          created_at: new Date().toISOString(),
        }]);
      }
    } catch (err: any) {
      if (err.name !== 'AbortError') {
        setMessages(prev => [...prev, {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: `Error: ${err.message}`,
          created_at: new Date().toISOString(),
        }]);
      }
    } finally {
      setIsStreaming(false);
      setStreamingContent('');
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-slate-700">
        <div>
          <h1 className="text-lg font-semibold">Chat</h1>
          <p className="text-xs text-slate-400">
            {conversationId ? `Session: ${conversationId.slice(0, 8)}...` : 'New conversation'}
          </p>
        </div>
        <button
          onClick={handleNewConversation}
          className="flex items-center gap-2 px-3 py-2 bg-slate-700 rounded-lg hover:bg-slate-600 transition-colors text-sm"
        >
          <Plus size={16} /> New Chat
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !streamingContent && (
          <div className="flex items-center justify-center h-full text-slate-500">
            <div className="text-center">
              <MessageSquareIcon className="mx-auto mb-4 w-12 h-12 opacity-50" />
              <p className="text-lg">Start a conversation</p>
              <p className="text-sm mt-1">Messages are logged with inference metadata</p>
            </div>
          </div>
        )}

        {messages.map((msg) => (
          <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div
              className={`max-w-[70%] px-4 py-3 rounded-2xl ${
                msg.role === 'user'
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-700 text-slate-100'
              }`}
            >
              <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
            </div>
          </div>
        ))}

        {/* Streaming indicator */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[70%] px-4 py-3 rounded-2xl bg-slate-700 text-slate-100">
              <p className="whitespace-pre-wrap text-sm">{streamingContent}</p>
              <span className="inline-block w-2 h-4 bg-blue-400 animate-pulse ml-1" />
            </div>
          </div>
        )}

        {isStreaming && !streamingContent && (
          <div className="flex justify-start">
            <div className="px-4 py-3 rounded-2xl bg-slate-700">
              <div className="flex gap-1">
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <span className="w-2 h-2 bg-slate-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-slate-700">
        <div className="flex items-center gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
            placeholder="Type a message..."
            className="flex-1 px-4 py-3 bg-slate-800 border border-slate-600 rounded-xl text-sm focus:outline-none focus:border-blue-500 transition-colors"
            disabled={isStreaming}
          />
          {isStreaming ? (
            <button
              onClick={handleCancel}
              className="p-3 bg-red-600 rounded-xl hover:bg-red-500 transition-colors"
            >
              <StopCircle size={20} />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className="p-3 bg-blue-600 rounded-xl hover:bg-blue-500 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Send size={20} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function MessageSquareIcon({ className }: { className?: string }) {
  return (
    <svg className={className} fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}
