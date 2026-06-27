import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { Shield, Lock, Mail, Loader2, AlertCircle, Cpu, HardDrive, EyeOff, CheckSquare, Sparkles } from 'lucide-react';

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { login } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    setError(null);

    try {
      const payload = {
        email: email,
        password: password
      };

      const response = await api.post('/api/v1/auth/login', payload);
      
      await login(response.access_token, response.refresh_token);
      navigate('/');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Incorrect email or password.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDemoLogin = async () => {
    setIsLoading(true);
    setError(null);
    
    const demoEmail = "demo@enterprise-rag.ai";
    const demoPassword = "Demo@123";
    
    // Simulate auto-typing effect for UX delight
    try {
      for (let i = 0; i <= demoEmail.length; i++) {
        setEmail(demoEmail.substring(0, i));
        await new Promise((resolve) => setTimeout(resolve, 35));
      }
      for (let i = 0; i <= demoPassword.length; i++) {
        setPassword(demoPassword.substring(0, i));
        await new Promise((resolve) => setTimeout(resolve, 35));
      }
      
      const response = await api.post('/api/v1/auth/login', {
        email: demoEmail,
        password: demoPassword
      });
      
      await login(response.access_token, response.refresh_token);
      navigate('/');
    } catch (err: any) {
      console.error(err);
      setError(err.message || 'Failed to authenticate under demo session.');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen bg-[#07090e] text-white relative overflow-hidden font-sans">
      {/* Moving Glowing Orbs Particle Effects */}
      <div className="absolute top-[-10%] left-[-10%] w-[550px] h-[550px] rounded-full bg-brand-500/10 blur-[130px] animate-pulse pointer-events-none"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[550px] h-[550px] rounded-full bg-accent-teal/10 blur-[130px] animate-pulse pointer-events-none"></div>

      {/* Grid Background Overlay */}
      <div className="absolute inset-0 bg-[linear-gradient(to_right,#0f172a15_1px,transparent_1px),linear-gradient(to_bottom,#0f172a15_1px,transparent_1px)] bg-[size:4rem_4rem] [mask-image:radial-gradient(ellipse_60%_50%_at_50%_0%,#000_70%,transparent_100%)] pointer-events-none"></div>

      <div className="w-full flex flex-col lg:flex-row max-w-7xl mx-auto z-10 relative">
        
        {/* Left Side: Brand Panel */}
        <div className="hidden lg:flex lg:w-1/2 flex-col justify-between p-12 relative border-r border-gray-900/40">
          <div>
            {/* Logo */}
            <div className="flex items-center gap-2.5 mb-16">
              <div className="p-2.5 bg-brand-500/15 border border-brand-500/25 rounded-2xl text-brand-400 shadow-inner">
                <Shield className="h-6 w-6" />
              </div>
              <span className="font-extrabold text-xl tracking-tight bg-gradient-to-r from-white via-gray-100 to-gray-400 bg-clip-text text-transparent">Enterprise RAG</span>
            </div>

            {/* Headline */}
            <div className="space-y-4 max-w-md">
              <h2 className="text-3xl font-extrabold leading-tight text-white">
                Private Document Intelligence, Grounded Locally.
              </h2>
              <p className="text-gray-400 text-sm leading-relaxed">
                Securely upload internal assets and interact with document knowledge stores offline. Completely isolated within the on-premise corporate perimeter.
              </p>
            </div>

            {/* Feature Grid */}
            <div className="grid grid-cols-2 gap-6 mt-12">
              <div className="flex gap-3">
                <div className="p-2 h-9 w-9 bg-brand-500/5 border border-brand-500/10 rounded-xl text-brand-400 shrink-0">
                  <Cpu className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-300">Local AI Inferences</h4>
                  <p className="text-gray-500 text-[11px] mt-0.5">Mistral 7B pipelines running locally on secure GPU servers.</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="p-2 h-9 w-9 bg-brand-500/5 border border-brand-500/10 rounded-xl text-brand-400 shrink-0">
                  <HardDrive className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-300">FAISS Indexing</h4>
                  <p className="text-gray-500 text-[11px] mt-0.5">Isolated vector search scoping document libraries by department.</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="p-2 h-9 w-9 bg-brand-500/5 border border-brand-500/10 rounded-xl text-brand-400 shrink-0">
                  <EyeOff className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-300">Data Sovereignty</h4>
                  <p className="text-gray-500 text-[11px] mt-0.5">No document chunk or user queries ever transit external cloud APIs.</p>
                </div>
              </div>

              <div className="flex gap-3">
                <div className="p-2 h-9 w-9 bg-brand-500/5 border border-brand-500/10 rounded-xl text-brand-400 shrink-0">
                  <CheckSquare className="h-5 w-5" />
                </div>
                <div>
                  <h4 className="text-xs font-bold uppercase tracking-wider text-gray-300">RBAC Controls</h4>
                  <p className="text-gray-500 text-[11px] mt-0.5">Strict authorization permissions scoped using secure JWT signatures.</p>
                </div>
              </div>
            </div>
          </div>

          {/* Footer branding */}
          <div className="text-xs text-gray-600 font-semibold tracking-wider uppercase">
            🛡️ Security Audit Verified Compliance
          </div>
        </div>

        {/* Right Side: Auth Forms Card */}
        <div className="flex-1 flex items-center justify-center p-8 lg:p-12">
          <div className="w-full max-w-md glass-panel rounded-3xl p-8 border border-gray-900/50 shadow-2xl relative">
            
            {/* Header branding on mobile */}
            <div className="flex flex-col items-center gap-2 mb-8 text-center lg:hidden">
              <div className="p-2.5 bg-brand-500/10 border border-brand-500/20 rounded-2xl text-brand-400">
                <Shield className="h-8 w-8" />
              </div>
              <h1 className="text-xl font-bold tracking-tight text-white">Enterprise RAG</h1>
            </div>

            <div className="mb-6">
              <h3 className="text-xl font-bold text-white">Sign In</h3>
              <p className="text-gray-500 text-xs mt-1">Authenticate using your corporate workstation credentials</p>
            </div>

            {/* Error Alert */}
            {error && (
              <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm">
                <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
                <span>{error}</span>
              </div>
            )}

            {/* Login Form */}
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider">Corporate Email</label>
                <div className="relative">
                  <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-550" />
                  <input
                    type="email"
                    required
                    className="w-full pl-10 pr-4 py-3 bg-darkSurface border border-gray-800 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all text-sm shadow-inner"
                    placeholder="you@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-bold text-gray-400 mb-2 uppercase tracking-wider">Password</label>
                <div className="relative">
                  <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-550" />
                  <input
                    type="password"
                    required
                    className="w-full pl-10 pr-4 py-3 bg-darkSurface border border-gray-800 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 transition-all text-sm shadow-inner"
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    disabled={isLoading}
                  />
                </div>
              </div>

              <button
                type="submit"
                className="w-full py-3 px-4 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all hover:shadow-lg disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer text-sm"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    <span>Verifying session...</span>
                  </>
                ) : (
                  <span>Sign In</span>
                )}
              </button>

              {/* Divider */}
              <div className="relative py-2 flex items-center justify-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-900"></div>
                </div>
                <span className="relative bg-darkSurface/90 px-3 text-[10px] uppercase font-bold text-gray-600 tracking-wider">Or Explore Platform</span>
              </div>

              {/* Recruiter Quick Access Demo Button */}
              <button
                type="button"
                onClick={handleDemoLogin}
                className="w-full py-3 px-4 bg-brand-500/10 hover:bg-brand-500/15 border border-brand-500/20 text-brand-350 hover:text-brand-300 font-semibold rounded-xl flex items-center justify-center gap-2 transition-all cursor-pointer text-sm"
                disabled={isLoading}
              >
                <Sparkles className="h-4 w-4 text-brand-400" />
                <span>Explore Demo Environment</span>
              </button>
            </form>
          </div>
        </div>
      </div>
    </div>
  );
};
