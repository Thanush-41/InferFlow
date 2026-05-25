import { useState, useEffect, useMemo } from "react";
import { Trash2, XCircle, Play, MessageSquare, Search, RefreshCw } from "lucide-react";
import {
  listConversations, cancelConversation, resumeConversation,
  deleteConversation, ConversationListItem,
} from "../api";

const STATUS_FILTERS = ["", "active", "cancelled", "completed"] as const;

const STATUS_STYLE: Record<string, { dot: string; badge: string }> = {
  active:    { dot: "bg-emerald-400", badge: "bg-emerald-500/15 text-emerald-400 border-emerald-500/25" },
  cancelled: { dot: "bg-red-400",     badge: "bg-red-500/15 text-red-400 border-red-500/25"             },
  completed: { dot: "bg-blue-400",    badge: "bg-blue-500/15 text-blue-400 border-blue-500/25"          },
};

export default function ConversationsPage() {
  const [conversations, setConversations] = useState<ConversationListItem[]>([]);
  const [filter,        setFilter]        = useState<string>("");
  const [search,        setSearch]        = useState("");
  const [loading,       setLoading]       = useState(true);

  const fetchConversations = async () => {
    setLoading(true);
    try {
      const data = await listConversations(filter || undefined);
      setConversations(data);
    } catch (err) {
      console.error("Failed to fetch conversations", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchConversations(); }, [filter]);

  const displayed = useMemo(() => {
    if (!search.trim()) return conversations;
    const q = search.toLowerCase();
    return conversations.filter((c) =>
      (c.title || "").toLowerCase().includes(q)
    );
  }, [conversations, search]);

  const handleCancel = async (id: string) => { await cancelConversation(id); fetchConversations(); };
  const handleResume = async (id: string) => { await resumeConversation(id); fetchConversations(); };
  const handleDelete = async (id: string) => {
    if (confirm("Permanently delete this conversation?")) {
      await deleteConversation(id);
      fetchConversations();
    }
  };

  const counts = useMemo(
    () => ({
      "": conversations.length,
      active:    conversations.filter((c) => c.status === "active").length,
      cancelled: conversations.filter((c) => c.status === "cancelled").length,
      completed: conversations.filter((c) => c.status === "completed").length,
    }),
    [conversations]
  );

  return (
    <div className="flex flex-col h-full bg-[#0d0f17]">

      {/* Header */}
      <div className="px-5 py-4 border-b border-[#252836] bg-[#161921]/80 backdrop-blur-sm">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h1 className="text-[14px] font-semibold text-slate-100">Conversations</h1>
            <p className="text-[11px] text-slate-500 mt-0.5">{conversations.length} total</p>
          </div>
          <button
            onClick={fetchConversations}
            disabled={loading}
            className="p-2 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-white/5 transition-all disabled:opacity-50"
            title="Refresh"
          >
            <RefreshCw size={15} className={loading ? "animate-spin" : ""} />
          </button>
        </div>

        {/* Search */}
        <div className="relative mb-3">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600 pointer-events-none" />
          <input
            type="text"
            placeholder="Search by title…"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full bg-[#1c1f2e] border border-[#252836] rounded-xl pl-8 pr-3 py-2 text-[12px] text-slate-300 placeholder-slate-600 focus:outline-none focus:border-blue-500/50 transition-colors"
          />
        </div>

        {/* Status filters */}
        <div className="flex gap-1.5 overflow-x-auto pb-0.5">
          {STATUS_FILTERS.map((s) => (
            <button
              key={s}
              onClick={() => setFilter(s)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium whitespace-nowrap transition-all ${
                filter === s
                  ? "bg-blue-600/20 text-blue-400 border border-blue-500/30"
                  : "text-slate-500 bg-[#1c1f2e] border border-[#252836] hover:text-slate-300 hover:border-[#2e3147]"
              }`}
            >
              {s ? (
                <span className={`w-1.5 h-1.5 rounded-full ${STATUS_STYLE[s]?.dot}`} />
              ) : null}
              {s ? s.charAt(0).toUpperCase() + s.slice(1) : "All"}
              <span className="ml-0.5 text-slate-600">{counts[s as keyof typeof counts] ?? 0}</span>
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto p-4">
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-600">
            <RefreshCw size={20} className="animate-spin mb-3" />
            <span className="text-[12px]">Loading…</span>
          </div>
        ) : displayed.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-20 text-slate-600">
            <MessageSquare size={28} className="mb-3 opacity-40" />
            <p className="text-[13px]">No conversations found</p>
            {search && (
              <button onClick={() => setSearch("")} className="mt-2 text-[11px] text-blue-500 hover:text-blue-400">
                Clear search
              </button>
            )}
          </div>
        ) : (
          <div className="max-w-2xl mx-auto space-y-2">
            {displayed.map((conv) => (
              <ConvCard
                key={conv.id}
                conv={conv}
                onCancel={() => handleCancel(conv.id)}
                onResume={() => handleResume(conv.id)}
                onDelete={() => handleDelete(conv.id)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ConvCard({
  conv, onCancel, onResume, onDelete,
}: {
  conv: ConversationListItem;
  onCancel: () => void;
  onResume: () => void;
  onDelete: () => void;
}) {
  const st = STATUS_STYLE[conv.status] ?? STATUS_STYLE.completed;

  return (
    <div className="flex items-center gap-3 px-4 py-3.5 bg-[#161921] border border-[#252836] rounded-2xl hover:border-[#2e3147] transition-all animate-fade-up">
      {/* Status dot */}
      <div className={`w-2 h-2 rounded-full flex-shrink-0 ${st.dot}`} />

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-[13px] font-medium text-slate-200 truncate">
            {conv.title || "Untitled conversation"}
          </p>
          <span className={`px-1.5 py-0.5 rounded-md text-[10px] font-semibold border flex-shrink-0 ${st.badge}`}>
            {conv.status}
          </span>
        </div>
        <p className="text-[11px] text-slate-600">
          {conv.message_count} msg · {timeAgo(conv.updated_at)}
        </p>
      </div>

      {/* Actions */}
      <div className="flex items-center gap-0.5 flex-shrink-0">
        {conv.status === "active" && (
          <ActionBtn onClick={onCancel} title="Cancel" icon={XCircle} color="yellow" />
        )}
        {conv.status === "cancelled" && (
          <ActionBtn onClick={onResume} title="Resume" icon={Play} color="emerald" />
        )}
        <ActionBtn onClick={onDelete} title="Delete" icon={Trash2} color="red" />
      </div>
    </div>
  );
}

function ActionBtn({
  onClick, title, icon: Icon, color,
}: { onClick: () => void; title: string; icon: React.ElementType; color: string }) {
  const c: Record<string, string> = {
    yellow:  "hover:bg-yellow-500/10  text-slate-600 hover:text-yellow-400",
    emerald: "hover:bg-emerald-500/10 text-slate-600 hover:text-emerald-400",
    red:     "hover:bg-red-500/10     text-slate-600 hover:text-red-400",
  };
  return (
    <button
      onClick={onClick}
      title={title}
      className={`p-2 rounded-xl transition-all ${c[color]}`}
    >
      <Icon size={14} />
    </button>
  );
}

function timeAgo(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const s = Math.floor(diff / 1000);
  if (s < 60)   return "just now";
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  if (s < 86400)return `${Math.floor(s / 3600)}h ago`;
  return `${Math.floor(s / 86400)}d ago`;
}
