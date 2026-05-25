import { useState } from "react";
import { BrowserRouter, Routes, Route, NavLink } from "react-router-dom";
import { MessageSquare, BarChart3, List, Cpu, Menu, X } from "lucide-react";
import ChatPage from "./pages/ChatPage";
import ConversationsPage from "./pages/ConversationsPage";
import DashboardPage from "./pages/DashboardPage";

const NAV = [
  { to: "/",              end: true,  icon: MessageSquare, label: "Chat"      },
  { to: "/conversations", end: false, icon: List,          label: "History"   },
  { to: "/dashboard",     end: false, icon: BarChart3,     label: "Dashboard" },
] as const;

function Logo() {
  return (
    <div className="flex items-center gap-3">
      <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-900/40 flex-shrink-0">
        <Cpu size={15} className="text-white" />
      </div>
      <span className="font-bold tracking-tight bg-gradient-to-r from-blue-400 to-indigo-400 bg-clip-text text-transparent text-[15px]">
        InferFlow
      </span>
    </div>
  );
}

function NavItem({
  to, end, icon: Icon, label, onClick,
}: { to: string; end: boolean; icon: React.ElementType; label: string; onClick?: () => void }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      className={({ isActive }) =>
        `flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13px] font-medium transition-all duration-150 ${
          isActive
            ? "bg-blue-600/20 text-blue-400 border border-blue-500/25"
            : "text-slate-400 hover:text-slate-200 hover:bg-white/[0.04]"
        }`
      }
    >
      <Icon size={16} />
      <span>{label}</span>
    </NavLink>
  );
}

export default function App() {
  const [open, setOpen] = useState(false);

  return (
    <BrowserRouter>
      <div className="flex h-[100dvh] bg-[#0d0f17] text-slate-100 overflow-hidden">

        {/* Desktop sidebar */}
        <aside className="hidden md:flex w-52 flex-shrink-0 flex-col bg-[#161921] border-r border-[#252836]">
          <div className="px-4 py-4 border-b border-[#252836]">
            <Logo />
          </div>
          <nav className="flex flex-col gap-0.5 p-3 flex-1">
            {NAV.map((item) => <NavItem key={item.to} {...item} />)}
          </nav>
          <div className="px-4 py-3 border-t border-[#252836]">
            <p className="text-[11px] text-slate-600 font-medium uppercase tracking-widest">LLM Observability</p>
          </div>
        </aside>

        {/* Mobile overlay sidebar */}
        {open && (
          <div className="md:hidden fixed inset-0 z-50 flex">
            <aside className="w-56 flex flex-col bg-[#161921] border-r border-[#252836] shadow-2xl">
              <div className="flex items-center justify-between px-4 py-4 border-b border-[#252836]">
                <Logo />
                <button
                  onClick={() => setOpen(false)}
                  className="text-slate-500 hover:text-slate-200 p-1.5 rounded-lg hover:bg-white/5 transition-colors"
                >
                  <X size={17} />
                </button>
              </div>
              <nav className="flex flex-col gap-0.5 p-3">
                {NAV.map((item) => <NavItem key={item.to} {...item} onClick={() => setOpen(false)} />)}
              </nav>
            </aside>
            <div className="flex-1 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
          </div>
        )}

        {/* Page area */}
        <div className="flex flex-col flex-1 min-w-0">

          {/* Mobile topbar */}
          <header className="md:hidden flex items-center gap-3 px-4 py-3 bg-[#161921] border-b border-[#252836]">
            <button
              onClick={() => setOpen(true)}
              className="text-slate-400 hover:text-slate-200 p-1.5 rounded-lg hover:bg-white/5 transition-colors"
            >
              <Menu size={19} />
            </button>
            <Logo />
          </header>

          <main className="flex-1 overflow-hidden">
            <Routes>
              <Route path="/"              element={<ChatPage />}         />
              <Route path="/conversations" element={<ConversationsPage />} />
              <Route path="/dashboard"     element={<DashboardPage />}    />
            </Routes>
          </main>

          {/* Mobile bottom nav */}
          <nav className="md:hidden flex items-center border-t border-[#252836] bg-[#161921]">
            {NAV.map(({ to, end, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={end}
                className={({ isActive }) =>
                  `flex-1 flex flex-col items-center gap-1 py-2.5 text-[11px] font-medium transition-colors ${
                    isActive ? "text-blue-400" : "text-slate-500 hover:text-slate-300"
                  }`
                }
              >
                <Icon size={19} />
                {label}
              </NavLink>
            ))}
          </nav>
        </div>
      </div>
    </BrowserRouter>
  );
}
