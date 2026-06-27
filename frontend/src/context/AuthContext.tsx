import React, { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

export interface UserProfile {
  id: string;
  email: string;
  full_name: string;
  role_id: string; // ADMIN, MANAGER, ENGINEER, VIEWER
  department_id: string | null;
  department_name: string | null;
  permissions: string[];
}

interface AuthContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  loading: boolean;
  login: (accessToken: string, refreshToken: string) => Promise<void>;
  logout: () => void;
  refreshProfile: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = async () => {
    try {
      const profile = await api.get('/api/v1/users/me');
      setUser(profile);
      localStorage.setItem('user_profile', JSON.stringify(profile));
    } catch (err) {
      console.error('Failed to load user profile:', err);
      // If profile fetch fails (e.g. invalid token), log out
      api.logout();
      setUser(null);
    }
  };

  useEffect(() => {
    const initializeAuth = async () => {
      const token = localStorage.getItem('access_token');
      const cachedProfile = localStorage.getItem('user_profile');

      if (token) {
        if (cachedProfile) {
          try {
            setUser(JSON.parse(cachedProfile));
          } catch {
            // Ignore parse errors and fetch fresh
          }
        }
        await fetchProfile();
      }
      setLoading(false);
    };

    initializeAuth();
  }, []);

  const login = async (accessToken: string, refreshToken: string) => {
    setLoading(true);
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
    await fetchProfile();
    setLoading(false);
  };

  const logout = () => {
    api.logout();
    setUser(null);
  };

  const refreshProfile = async () => {
    await fetchProfile();
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, loading, login, logout, refreshProfile }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
