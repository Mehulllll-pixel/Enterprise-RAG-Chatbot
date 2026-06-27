import React from 'react';
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ChatConsole } from './pages/ChatConsole';
import { DocumentLibrary } from './pages/DocumentLibrary';
import { AdminConsole } from './pages/AdminConsole';
import { Shield, MessageSquare, FileText, Users, LogOut, User as UserIcon } from 'lucide-react';

const NavigationHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();

  if (!user) return null;

  const isAdmin = user.role_id === 'ADMIN';

  const linkClass = (path: string) => {
    const base = "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all";
    if (location.pathname === path) {
      return `${base} bg-brand-500/10 text-brand-400 border border-brand-500/10`;
    }
    return `${base} text-gray-400 hover:text-white hover:bg-gray-900 border border-transparent`;
  };

  return (
    <header className="h-16 border-b border-gray-900/60 bg-darkSurface px-6 flex items-center justify-between sticky top-0 z-30">
      {/* Brand logo */}
      <div className="flex items-center gap-2.5">
        <div className="p-1.5 bg-brand-500/10 border border-brand-500/20 rounded-lg text-brand-400 shadow-inner">
          <Shield className="h-5 w-5" />
        </div>
        <span className="font-bold text-white text-base tracking-tight">Enterprise RAG</span>
      </div>

      {/* Nav links */}
      <nav className="hidden md:flex items-center gap-3">
        <Link to="/" className={linkClass('/')}>
          <MessageSquare className="h-4 w-4" />
          <span>Chat Console</span>
        </Link>
        <Link to="/documents" className={linkClass('/documents')}>
          <FileText className="h-4 w-4" />
          <span>Document Library</span>
        </Link>
        {isAdmin && (
          <Link to="/admin" className={linkClass('/admin')}>
            <Users className="h-4 w-4" />
            <span>Admin Directory</span>
          </Link>
        )}
      </nav>

      {/* Profile info & Logout */}
      <div className="flex items-center gap-4">
        {/* User Card info */}
        <div className="hidden lg:flex items-center gap-2.5 pl-4 border-l border-gray-900/60">
          <div className="p-1.5 bg-gray-800 rounded-lg text-gray-400">
            <UserIcon className="h-4 w-4" />
          </div>
          <div className="flex flex-col text-left">
            <span className="text-white text-xs font-semibold">{user.full_name}</span>
            <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">{user.role_id} • {user.department_name || 'Global'}</span>
          </div>
        </div>

        {/* Logout */}
        <button
          onClick={logout}
          className="flex items-center gap-2 px-3 py-2 border border-gray-800 hover:border-red-900/20 text-gray-400 hover:text-red-400 hover:bg-red-500/5 rounded-xl text-sm font-medium transition-all"
        >
          <LogOut className="h-4 w-4" />
          <span className="hidden sm:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
};

const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* Protected Layout */}
      <Route path="/" element={
        <ProtectedRoute>
          <NavigationHeader />
          <ChatConsole />
        </ProtectedRoute>
      } />

      <Route path="/documents" element={
        <ProtectedRoute>
          <NavigationHeader />
          <DocumentLibrary />
        </ProtectedRoute>
      } />

      <Route path="/admin" element={
        <ProtectedRoute requiredPermission="user:write">
          <NavigationHeader />
          <AdminConsole />
        </ProtectedRoute>
      } />

      {/* Fallback routing redirects */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
