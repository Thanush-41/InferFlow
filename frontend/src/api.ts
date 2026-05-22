const API_BASE = '/api';

// Default model/provider — override via VITE_DEFAULT_MODEL / VITE_DEFAULT_PROVIDER in frontend/.env
const DEFAULT_MODEL = import.meta.env.VITE_DEFAULT_MODEL || 'gemini-2.5-flash';
const DEFAULT_PROVIDER = import.meta.env.VITE_DEFAULT_PROVIDER || 'gemini';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  created_at: string;
}

export interface Conversation {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
}

export interface ConversationListItem {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface DashboardMetrics {
  total_requests: number;
  avg_latency_ms: number;
  p95_latency_ms: number;
  p99_latency_ms: number;
  total_tokens: number;
  error_rate: number;
  requests_per_minute: number;
  active_conversations: number;
}

export interface ProviderStats {
  provider: string;
  model: string;
  total_requests: number;
  avg_latency_ms: number;
  error_count: number;
  total_tokens: number;
}

export interface LatencyBucket {
  timestamp: string;
  avg_latency_ms: number;
  request_count: number;
}

// Chat
export async function sendMessage(message: string, conversationId?: string, stream = true) {
  const body = {
    message,
    conversation_id: conversationId || null,
    model: DEFAULT_MODEL,
    provider: DEFAULT_PROVIDER,
    stream,
  };

  if (stream) {
    const response = await fetch(`${API_BASE}/chat/send/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    return response;
  }

  const response = await fetch(`${API_BASE}/chat/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return response.json();
}

// Conversations
export async function listConversations(status?: string): Promise<ConversationListItem[]> {
  const params = status ? `?status=${status}` : '';
  const res = await fetch(`${API_BASE}/conversations/${params}`);
  return res.json();
}

export async function getConversation(id: string): Promise<Conversation> {
  const res = await fetch(`${API_BASE}/conversations/${id}`);
  return res.json();
}

export async function cancelConversation(id: string) {
  const res = await fetch(`${API_BASE}/conversations/${id}/cancel`, { method: 'POST' });
  return res.json();
}

export async function resumeConversation(id: string) {
  const res = await fetch(`${API_BASE}/conversations/${id}/resume`, { method: 'POST' });
  return res.json();
}

export async function deleteConversation(id: string) {
  const res = await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' });
  return res.json();
}

// Dashboard
export async function getDashboardMetrics(hours = 24): Promise<DashboardMetrics> {
  const res = await fetch(`${API_BASE}/dashboard/metrics?hours=${hours}`);
  return res.json();
}

export async function getLatencyData(hours = 24): Promise<LatencyBucket[]> {
  const res = await fetch(`${API_BASE}/dashboard/latency?hours=${hours}`);
  return res.json();
}

export async function getProviderStats(hours = 24): Promise<ProviderStats[]> {
  const res = await fetch(`${API_BASE}/dashboard/providers?hours=${hours}`);
  return res.json();
}

export async function getErrors(hours = 24) {
  const res = await fetch(`${API_BASE}/dashboard/errors?hours=${hours}`);
  return res.json();
}

export async function getThroughput(hours = 24) {
  const res = await fetch(`${API_BASE}/dashboard/throughput?hours=${hours}`);
  return res.json();
}
