import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Trash2, XCircle, Play, MessageSquare } from 'lucide-react';
import {
  listConversations,
  cancelConversation,
  resumeConversation,
  deleteConversation,
  ConversationListItem,
} from '../api';

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [filter, setFilter] = useState<string>('');
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const data = await listConversations(filter || undefined);
      setConversations(data);
    } catch (err) {
      console.error('Failed to fetch conversations', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchConversations();
  }, [filter]);

  const handleCancel = async (id: string) => {
    await cancelConversation(id);
    fetchConversations();
  };

  const handleResume = async (id: string) => {
    await resumeConversation(id);
    fetchConversations();
  };

  const handleDelete = async (id: string) => {
    if (confirm('Delete this conversation?')) {
      await deleteConversation(id);
      fetchConversations();
    }
  };

  const statusColor = (status: string) => {
    switch (status) {
      case 'active': return 'bg-green-500/20 text-green-400';
      case 'cancelled': return 'bg-red-500/20 text-red-400';
      case 'completed': return 'bg-blue-500/20 text-blue-400';
      default: return 'bg-slate-500/20 text-slate-400';
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="p-4 border-b border-slate-700">
        <h1 className="text-lg font-semibold mb-3">Conversations</h1>
        <div className="flex gap-2">
          {['', 'active', 'cancelled', 'completed'].map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                filter === s ? 'bg-blue-600' : 'bg-slate-700 hover:bg-slate-600'
              }`}
            >
              {s || 'All'}
            </button>
          ))}
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-2">
        {loading ? (
          <div className="text-center text-slate-400 py-8">Loading...</div>
        ) : conversations.length === 0 ? (
          <div className="text-center text-slate-400 py-8">No conversations found</div>
        ) : (
          conversations.map((conv) => (
            <div
              key={conv.id}
              className="flex items-center justify-between p-4 bg-slate-800 rounded-xl border border-slate-700 hover:border-slate-600 transition-colors"
            >
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <h3 className="text-sm font-medium truncate">
                    {conv.title || 'Untitled'}
                  </h3>
                  <span className={`px-2 py-0.5 rounded-full text-xs ${statusColor(conv.status)}`}>
                    {conv.status}
                  </span>
                </div>
                <p className="text-xs text-slate-400">
                  {conv.message_count} messages · {new Date(conv.updated_at).toLocaleString()}
                </p>
              </div>

              <div className="flex items-center gap-1 ml-4">
                {conv.status === 'active' && (
                  <button
                    onClick={() => handleCancel(conv.id)}
                    className="p-2 rounded-lg hover:bg-slate-700 text-yellow-400"
                    title="Cancel"
                  >
                    <XCircle size={16} />
                  </button>
                )}
                {conv.status === 'cancelled' && (
                  <button
                    onClick={() => handleResume(conv.id)}
                    className="p-2 rounded-lg hover:bg-slate-700 text-green-400"
                    title="Resume"
                  >
                    <Play size={16} />
                  </button>
                )}
                <button
                  onClick={() => handleDelete(conv.id)}
                  className="p-2 rounded-lg hover:bg-slate-700 text-red-400"
                  title="Delete"
                >
                  <Trash2 size={16} />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
