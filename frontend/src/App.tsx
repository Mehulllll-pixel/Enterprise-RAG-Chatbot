import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Login } from './pages/Login';
import { Register } from './pages/Register';
import { ChatConsole } from './pages/ChatConsole';
import { DocumentLibrary } from './pages/DocumentLibrary';
import { AdminConsole } from './pages/AdminConsole';
import { Shield, MessageSquare, FileText, Users, LogOut, User as UserIcon, Menu, X } from 'lucide-react';

const NavigationHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  if (!user) return null;

  const isAdmin = user.role_id === 'ADMIN';

  const linkClass = (path: string) => {
    const base = "flex items-center gap-2 px-4 py-2 rounded-xl text-sm font-medium transition-all cursor-pointer";
    if (location.pathname === path) {
      return `${base} bg-brand-500/10 text-brand-400 border border-brand-500/10`;
    }
    return `${base} text-gray-400 hover:text-white hover:bg-gray-900 border border-transparent`;
  };

  const mobileLinkClass = (path: string) => {
    const base = "flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all w-full cursor-pointer";
    if (location.pathname === path) {
      return `${base} bg-brand-500/10 text-brand-450 border border-brand-500/15`;
    }
    return `${base} text-gray-400 hover:text-white hover:bg-gray-900 border border-transparent`;
  };

  return (
    <>
      <header className="h-16 border-b border-gray-900/60 bg-darkSurface px-4 md:px-6 flex items-center justify-between sticky top-0 z-30 font-sans">
        
        {/* Left Side: Brand Logo */}
        <div className="flex items-center gap-2.5">
          <div className="p-1.5 bg-brand-500/15 border border-brand-500/25 rounded-lg text-brand-400 shadow-inner">
            <Shield className="h-5 w-5" />
          </div>
          <span className="font-extrabold text-white text-base tracking-tight">Enterprise RAG</span>
        </div>

        {/* Center: Desktop Nav Links */}
        <nav className="hidden md:flex items-center gap-2">
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

        {/* Right Side: Profile Info, mobile burger, and Sign Out */}
        <div className="flex items-center gap-3">
          
          {/* User profile card (Desktop) */}
          <div className="hidden lg:flex items-center gap-2.5 pl-4 border-l border-gray-900/50">
            <div className="p-1.5 bg-gray-800/80 rounded-lg text-gray-400">
              <UserIcon className="h-4 w-4" />
            </div>
            <div className="flex flex-col text-left">
              <span className="text-white text-xs font-semibold">{user.full_name}</span>
              <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">{user.role_id} • {user.department_name || 'Global'}</span>
            </div>
          </div>

          {/* Sign Out (Desktop) */}
          <button
            onClick={logout}
            className="hidden sm:flex items-center gap-2 px-3 py-1.5 border border-gray-800 hover:border-red-900/20 text-gray-400 hover:text-red-400 hover:bg-red-500/5 rounded-xl text-xs font-semibold transition-all cursor-pointer"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>

          {/* Mobile Menu Toggle Button */}
          <button
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="md:hidden p-1.5 border border-gray-800 text-gray-400 rounded-xl hover:bg-gray-900 focus:outline-none"
          >
            {mobileMenuOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </button>

        </div>
      </header>

      {/* Mobile Drawer Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden fixed inset-x-0 top-16 bg-[#0a0d15] border-b border-gray-900/80 z-40 p-4 space-y-2 flex flex-col items-start font-sans shadow-2xl glass-panel">
          <Link 
            to="/" 
            className={mobileLinkClass('/')}
            onClick={() => setMobileMenuOpen(false)}
          >
            <MessageSquare className="h-4 w-4" />
            <span>Chat Console</span>
          </Link>
          <Link 
            to="/documents" 
            className={mobileLinkClass('/documents')}
            onClick={() => setMobileMenuOpen(false)}
          >
            <FileText className="h-4 w-4" />
            <span>Document Library</span>
          </Link>
          {isAdmin && (
            <Link 
              to="/admin" 
              className={mobileLinkClass('/admin')}
              onClick={() => setMobileMenuOpen(false)}
            >
              <Users className="h-4 w-4" />
              <span>Admin Directory</span>
            </Link>
          )}
          
          <div className="w-full border-t border-gray-900/60 my-2 pt-2"></div>
          
          <div className="flex items-center gap-3 px-4 py-2 w-full">
            <div className="p-1.5 bg-gray-800 rounded-lg text-gray-400 shrink-0">
              <UserIcon className="h-4 w-4" />
            </div>
            <div className="flex flex-col text-left truncate min-w-0">
              <span className="text-white text-xs font-semibold truncate">{user.full_name}</span>
              <span className="text-gray-500 text-[10px] uppercase font-bold tracking-wider">{user.role_id} • {user.department_name || 'Global'}</span>
            </div>
          </div>

          <button
            onClick={() => {
              setMobileMenuOpen(false);
              logout();
            }}
            className="w-full flex items-center gap-3 px-4 py-3 border border-red-900/20 text-red-400 bg-red-500/5 rounded-xl text-sm font-semibold transition-all cursor-pointer mt-1"
          >
            <LogOut className="h-4 w-4" />
            <span>Sign Out</span>
          </button>
        </div>
      )}
    </>
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
