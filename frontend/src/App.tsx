import { BrowserRouter, Routes, Route, NavLink } from 'react-router-dom';
import { MessageSquare, BarChart3, List } from 'lucide-react';
import ChatPage from './pages/ChatPage';
import ConversationsPage from './pages/ConversationsPage';
import DashboardPage from './pages/DashboardPage';

function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen bg-slate-900 text-white">
        {/* Sidebar */}
        <nav className="w-16 bg-slate-800 flex flex-col items-center py-4 gap-4 border-r border-slate-700">
          <NavLink
            to="/"
            className={({ isActive }) =>
              `p-3 rounded-lg transition-colors ${isActive ? 'bg-blue-600' : 'hover:bg-slate-700'}`
            }
            title="Chat"
          >
            <MessageSquare size={20} />
          </NavLink>
          <NavLink
            to="/conversations"
            className={({ isActive }) =>
              `p-3 rounded-lg transition-colors ${isActive ? 'bg-blue-600' : 'hover:bg-slate-700'}`
            }
            title="Conversations"
          >
            <List size={20} />
          </NavLink>
          <NavLink
            to="/dashboard"
            className={({ isActive }) =>
              `p-3 rounded-lg transition-colors ${isActive ? 'bg-blue-600' : 'hover:bg-slate-700'}`
            }
            title="Dashboard"
          >
            <BarChart3 size={20} />
          </NavLink>
        </nav>

        {/* Main Content */}
        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<ChatPage />} />
            <Route path="/conversations" element={<ConversationsPage />} />
            <Route path="/dashboard" element={<DashboardPage />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  );
}

export default App;
