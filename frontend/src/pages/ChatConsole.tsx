import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { api, API_BASE } from '../services/api';
import { 
  Plus, MessageSquare, Trash2, Send, Bot, User, 
  ChevronRight, Loader2, Sparkles, BookOpen, Clock, BarChart3
} from 'lucide-react';

interface MessageItem {
  id?: string;
  role: 'user' | 'assistant';
  content: string;
  citations?: any[];
  confidence_score?: number;
  related_questions?: string[];
  latency_ms?: number;
}

interface ChatSession {
  id: string;
  title: string;
  department_id: string | null;
  created_at: string;
}

export const ChatConsole: React.FC = () => {
  const { user } = useAuth();
  
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<MessageItem[]>([]);
  const [inputText, setInputText] = useState('');
  
  // Loading states
  const [sessionsLoading, setSessionsLoading] = useState(true);
  const [streamingResponse, setStreamingResponse] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  
  // Sidebar open on mobile
  const [sidebarOpen, setSidebarOpen] = useState(false);
  
  // Active citation side panel state
  const [activeCitations, setActiveCitations] = useState<any[] | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, streamingResponse]);

  // Load chat sessions on mount
  const fetchSessions = async () => {
    try {
      const response = await api.get('/api/v1/chats');
      setSessions(Array.isArray(response) ? response : []);
      
      // Auto-select first chat session if none active
      if (Array.isArray(response) && response.length > 0 && !activeSessionId) {
        handleSelectSession(response[0].id);
      }
    } catch (err) {
      console.error('Failed to load conversations:', err);
    } finally {
      setSessionsLoading(false);
    }
  };

  useEffect(() => {
    fetchSessions();
  }, []);

  const handleSelectSession = async (id: string) => {
    setActiveSessionId(id);
    setSidebarOpen(false);
    setStreamingResponse('');
    setIsStreaming(false);
    setActiveCitations(null);
    setMessages([]);
    
    try {
      const response = await api.get(`/api/v1/chats/${id}`);
      setMessages(response.messages || []);
    } catch (err) {
      console.error('Failed to load chat transcript:', err);
    }
  };

  const handleNewChat = async () => {
    try {
      const payload = {
        title: `Chat Session ${new Date().toLocaleDateString()}`,
        department_id: user?.department_id || null
      };
      const response = await api.post('/api/v1/chats', payload);
      setSessions(prev => [response, ...prev]);
      handleSelectSession(response.id);
    } catch (err) {
      console.error('Failed to create chat:', err);
    }
  };

  const handleDeleteChat = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!window.confirm('Delete this conversation history?')) return;
    
    try {
      await api.delete(`/api/v1/chats/${id}`);
      setSessions(prev => prev.filter(s => s.id !== id));
      if (activeSessionId === id) {
        setActiveSessionId(null);
        setMessages([]);
      }
    } catch (err) {
      console.error('Failed to delete chat:', err);
    }
  };

  // Main SSE reader streaming query answer
  const handleQuerySubmit = async (queryToSend: string) => {
    if (!queryToSend.trim() || !activeSessionId || isStreaming) return;
    
    // Reset inputs
    setInputText('');
    setIsStreaming(true);
    setStreamingResponse('');
    
    // Add user message to local feed immediately
    const userMsg: MessageItem = { role: 'user', content: queryToSend };
    setMessages(prev => [...prev, userMsg]);
    
    try {
      const token = localStorage.getItem('access_token');
      const response = await fetch(`${API_BASE}/api/v1/chats/${activeSessionId}/messages`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ content: queryToSend })
      });

      if (!response.ok) {
        throw new Error('Inference server returned error.');
      }

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      if (!reader) return;

      let accumulatedContent = '';
      let citationData: any[] = [];
      let confScore: number | undefined = undefined;
      let latency: number | undefined = undefined;
      let relatedQs: string[] | undefined = undefined;

      // Read SSE stream
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const rawChunk = decoder.decode(value);
        const lines = rawChunk.split('\n\n');
        
        for (const line of lines) {
          if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim();
            if (!dataStr) continue;

            try {
              const parsed = JSON.parse(dataStr);
              
              if (parsed.type === 'token') {
                accumulatedContent += parsed.content;
                setStreamingResponse(accumulatedContent);
              } 
              else if (parsed.type === 'metadata') {
                citationData = parsed.citations || [];
                confScore = parsed.confidence_score;
                latency = parsed.latency_ms;
                relatedQs = parsed.related_questions;
              }
            } catch (err) {
              console.error('Error parsing SSE JSON payload:', err, line);
            }
          }
        }
      }

      // Finish streaming and append assistant response to messages feed
      const assistantMsg: MessageItem = {
        role: 'assistant',
        content: accumulatedContent,
        citations: citationData,
        confidence_score: confScore,
        latency_ms: latency,
        related_questions: relatedQs
      };

      setMessages(prev => [...prev, assistantMsg]);
      setStreamingResponse('');
      setIsStreaming(false);
      
    } catch (err: any) {
      console.error(err);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: RAG pipeline execution failed. (${err.message || 'Check network connection'})`
      }]);
      setIsStreaming(false);
    }
  };

  const getConfidenceColorClass = (score: number) => {
    if (score >= 0.8) return 'text-emerald-400 border-emerald-500/20 bg-emerald-500/5';
    if (score >= 0.5) return 'text-yellow-400 border-yellow-500/20 bg-yellow-500/5';
    return 'text-red-400 border-red-500/20 bg-red-500/5';
  };

  // Custom regex formatting logic to support lists, headers, bold, and code blocks
  const renderInlineFormatting = (text: string) => {
    const boldParts = text.split(/(\*\*.*?\*\*)/g);
    return boldParts.map((bpart, bidx) => {
      if (bpart.startsWith('**') && bpart.endsWith('**')) {
        return <strong key={bidx} className="font-semibold text-white">{bpart.slice(2, -2)}</strong>;
      }
      return bpart;
    });
  };

  const renderMarkdown = (text: string) => {
    if (!text) return null;
    
    // Split on triple backticks for code blocks
    const parts = text.split(/(```[\s\S]*?```)/g);
    
    return parts.map((part, idx) => {
      if (part.startsWith('```') && part.endsWith('```')) {
        const codeLines = part.slice(3, -3).trim().split('\n');
        let language = 'code';
        if (codeLines[0] && codeLines[0].length < 15 && !codeLines[0].includes(' ') && !codeLines[0].includes('(')) {
          language = codeLines[0];
          codeLines.shift();
        }
        const code = codeLines.join('\n');
        return (
          <pre key={idx} className="bg-gray-950 border border-gray-900 text-gray-250 text-xs font-mono p-4 rounded-xl my-3.5 overflow-x-auto relative group shadow-inner">
            {language && (
              <span className="absolute top-2 right-3 text-[9px] uppercase font-bold tracking-wider text-gray-600 opacity-60 group-hover:opacity-100 transition-opacity">
                {language}
              </span>
            )}
            <code>{code}</code>
          </pre>
        );
      }
      
      const lines = part.split('\n');
      return (
        <div key={idx} className="space-y-2">
          {lines.map((line, lidx) => {
            if (line.startsWith('### ')) {
              return <h4 key={lidx} className="text-sm font-bold text-white mt-3.5 mb-1.5">{line.substring(4)}</h4>;
            }
            if (line.startsWith('## ')) {
              return <h3 key={lidx} className="text-base font-extrabold text-white mt-4 mb-2">{line.substring(3)}</h3>;
            }
            
            const trimmed = line.trim();
            if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
              const itemText = trimmed.substring(2);
              return (
                <ul key={lidx} className="list-disc pl-5 my-1">
                  <li className="text-sm leading-relaxed text-gray-300">
                    {renderInlineFormatting(itemText)}
                  </li>
                </ul>
              );
            }
            
            return (
              <p key={lidx} className="text-sm leading-relaxed text-gray-300">
                {renderInlineFormatting(line)}
              </p>
            );
          })}
        </div>
      );
    });
  };

  return (
    <div className="flex h-[calc(100vh-64px)] relative overflow-hidden bg-[#07090e]">
      
      {/* 1. Sidebar Nav Conversations list */}
      <div className={`absolute md:relative inset-y-0 left-0 w-80 bg-[#0c0f17] border-r border-gray-900/60 z-20 transition-transform duration-300 md:translate-x-0 flex flex-col ${
        sidebarOpen ? 'translate-x-0' : '-translate-x-full'
      }`}>
        <div className="p-4 border-b border-gray-900/60">
          <button
            onClick={handleNewChat}
            className="w-full flex items-center justify-center gap-2 py-2.5 px-4 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-xl transition-all shadow-md text-sm cursor-pointer"
          >
            <Plus className="h-4 w-4" />
            <span>New Conversation</span>
          </button>
        </div>

        {/* Sessions list */}
        <div className="flex-1 overflow-y-auto p-2 space-y-1">
          {sessionsLoading ? (
            <div className="p-2 space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <div key={i} className="h-10 bg-gray-900/40 border border-gray-900/20 rounded-xl animate-pulse flex items-center px-3 gap-2">
                  <div className="h-4 w-4 bg-gray-800 rounded-full shrink-0"></div>
                  <div className="h-3 bg-gray-800 rounded w-2/3"></div>
                </div>
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <div className="text-center py-10 text-gray-500 text-xs">
              No conversations started.
            </div>
          ) : (
            sessions.map((session) => (
              <div
                key={session.id}
                onClick={() => handleSelectSession(session.id)}
                className={`group flex items-center justify-between p-3 rounded-xl cursor-pointer transition-all border text-sm ${
                  activeSessionId === session.id
                    ? 'bg-brand-500/10 border-brand-500/20 text-brand-300'
                    : 'border-transparent text-gray-400 hover:bg-darkCard hover:text-white'
                }`}
              >
                <div className="flex items-center gap-2.5 truncate min-w-0">
                  <MessageSquare className="h-4 w-4 shrink-0 opacity-70" />
                  <span className="truncate">{session.title}</span>
                </div>
                <button
                  onClick={(e) => handleDeleteChat(session.id, e)}
                  className="p-1 hover:bg-red-500/20 text-gray-550 hover:text-red-400 rounded-lg transition-opacity md:opacity-0 group-hover:opacity-100 cursor-pointer"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Mobile sidebar overlay */}
      {sidebarOpen && (
        <div 
          onClick={() => setSidebarOpen(false)}
          className="absolute inset-0 bg-black/60 md:hidden z-10"
        />
      )}

      {/* 2. Main Chat Feed area */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#07090e] relative">
        {/* Mobile Header Bar */}
        <div className="md:hidden flex items-center justify-between p-3 border-b border-gray-900/60 bg-[#0c0f17]">
          <button
            onClick={() => setSidebarOpen(true)}
            className="p-2 border border-gray-800 text-gray-400 rounded-xl hover:bg-gray-800"
          >
            <MessageSquare className="h-5 w-5" />
          </button>
          <span className="text-white text-sm font-semibold truncate">Chat Console</span>
          <button
            onClick={handleNewChat}
            className="p-2 bg-brand-500 text-white rounded-xl"
          >
            <Plus className="h-5 w-5" />
          </button>
        </div>

        {/* Welcome Placeholder OR Message Feed */}
        {!activeSessionId ? (
          <div className="flex-1 flex items-center justify-center p-8 text-center">
            <div className="max-w-md space-y-6">
              <div className="p-4 bg-brand-500/5 border border-brand-500/10 rounded-3xl inline-block text-brand-400 shadow-inner pulse-glow">
                <Bot className="h-12 w-12" />
              </div>
              <div>
                <h2 className="text-2xl font-bold text-white mb-2">Welcome to Secure RAG Chat</h2>
                <p className="text-gray-400 text-sm">
                  Ask natural language questions grounded strictly in your department's documents.
                  No data ever leaves the on-premise servers.
                </p>
              </div>
              <button
                onClick={handleNewChat}
                className="px-6 py-3 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-xl transition-all shadow-lg text-sm inline-flex items-center gap-2 cursor-pointer"
              >
                <Sparkles className="h-4 w-4" />
                <span>Initialize Secure Session</span>
              </button>
            </div>
          </div>
        ) : (
          <div className="flex-1 flex flex-col min-h-0">
            {/* Conversations Feed */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6">
              {messages.length === 0 && !streamingResponse && (
                <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 p-8">
                  <Bot className="h-10 w-10 text-gray-700 mb-2" />
                  <p className="font-semibold text-gray-450">Secure pipeline connected</p>
                  <p className="text-xs text-gray-500 mt-1 max-w-sm">Ask a question to query policy files and generate citations.</p>
                </div>
              )}

              {/* Message cards rendering */}
              {messages.map((msg, index) => (
                <div 
                  key={index}
                  className={`flex gap-4 p-4 rounded-2xl max-w-3xl border ${
                    msg.role === 'user'
                      ? 'ml-auto bg-[#0d121f] border-gray-800/80 text-white flex-row-reverse shadow-sm'
                      : 'bg-[#0b0e14]/60 border-gray-900/60 text-gray-200'
                  }`}
                >
                  {/* Icon */}
                  <div className={`p-2.5 rounded-xl shrink-0 h-10 w-10 flex items-center justify-center border ${
                    msg.role === 'user'
                      ? 'bg-gray-850 border-gray-700 text-gray-300'
                      : 'bg-brand-500/10 border-brand-500/20 text-brand-400 shadow-inner'
                  }`}>
                    {msg.role === 'user' ? <User className="h-5 w-5" /> : <Bot className="h-5 w-5" />}
                  </div>

                  {/* Bubble text */}
                  <div className="space-y-3 min-w-0 flex-1">
                    {msg.role === 'user' ? (
                      <p className="text-sm leading-relaxed whitespace-pre-wrap text-white">{msg.content}</p>
                    ) : (
                      <div className="space-y-2">{renderMarkdown(msg.content)}</div>
                    )}

                    {/* Metadata Envelope: citations and latency */}
                    {msg.role === 'assistant' && (
                      <div className="flex flex-wrap items-center gap-3 pt-2.5 text-[10px] text-gray-500 border-t border-gray-900/30">
                        {msg.latency_ms !== undefined && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3.5 w-3.5 text-gray-650" />
                            <span>{msg.latency_ms} ms</span>
                          </span>
                        )}

                        {msg.confidence_score !== undefined && (
                          <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full border ${getConfidenceColorClass(msg.confidence_score)}`}>
                            <BarChart3 className="h-3 w-3" />
                            <span>Confidence: {Math.round(msg.confidence_score * 100)}%</span>
                          </span>
                        )}

                        {msg.citations && msg.citations.length > 0 && (
                          <button
                            onClick={() => setActiveCitations(msg.citations || null)}
                            className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-full bg-brand-500/10 hover:bg-brand-500/20 border border-brand-500/20 text-brand-300 transition-colors cursor-pointer"
                          >
                            <BookOpen className="h-3.5 w-3.5" />
                            <span>Sources ({msg.citations.length})</span>
                          </button>
                        )}
                      </div>
                    )}

                    {/* Related questions chips */}
                    {msg.role === 'assistant' && msg.related_questions && msg.related_questions.length > 0 && !isStreaming && (
                      <div className="pt-3 space-y-1.5 border-t border-gray-900/30 mt-3">
                        <span className="text-[9px] text-gray-600 font-bold block uppercase tracking-wider">Suggested Queries:</span>
                        <div className="flex flex-wrap gap-2">
                          {msg.related_questions.map((q, qidx) => (
                            <button
                              key={qidx}
                              onClick={() => handleQuerySubmit(q)}
                              className="text-left text-xs bg-darkCard hover:bg-gray-800 border border-gray-800/80 text-gray-400 hover:text-white rounded-xl py-1.5 px-3.5 transition-colors cursor-pointer flex items-center gap-1"
                            >
                              <span>{q}</span>
                              <ChevronRight className="h-3 w-3 shrink-0 opacity-40" />
                            </button>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Streaming Bubble Card */}
              {isStreaming && (
                <div className="flex gap-4 p-4 rounded-2xl max-w-3xl border bg-[#0b0e14]/60 border-gray-900/60 text-gray-250">
                  <div className="p-2.5 bg-brand-500/10 border border-brand-500/20 text-brand-400 rounded-xl h-10 w-10 shrink-0 flex items-center justify-center">
                    <Bot className="h-5 w-5 animate-pulse" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {!streamingResponse ? (
                      // Bouncing dots typing indicator bubble
                      <div className="flex items-center gap-1.5 py-3">
                        <span className="h-2.5 w-2.5 bg-brand-400 rounded-full animate-bounce shrink-0" style={{ animationDelay: '0ms' }}></span>
                        <span className="h-2.5 w-2.5 bg-brand-400 rounded-full animate-bounce shrink-0" style={{ animationDelay: '150ms' }}></span>
                        <span className="h-2.5 w-2.5 bg-brand-400 rounded-full animate-bounce shrink-0" style={{ animationDelay: '300ms' }}></span>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {renderMarkdown(streamingResponse)}
                        <span className="inline-flex items-center gap-1.5 text-xs text-brand-400 mt-2 font-medium">
                          <Loader2 className="h-3.5 w-3.5 animate-spin" />
                          <span>Generating response...</span>
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Input Bar panel */}
            <div className="p-4 border-t border-gray-900/60 bg-[#0c0f17]/40">
              <form 
                onSubmit={(e) => {
                  e.preventDefault();
                  handleQuerySubmit(inputText);
                }}
                className="max-w-3xl mx-auto relative"
              >
                <input
                  type="text"
                  className="w-full bg-darkSurface border border-gray-800 text-white rounded-2xl pl-4 pr-12 py-3.5 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm placeholder-gray-650 transition-colors shadow-inner"
                  placeholder="Ask a corporate grounding question (e.g. 'Can I work from home?')"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  disabled={isStreaming}
                />
                <button
                  type="submit"
                  disabled={!inputText.trim() || isStreaming}
                  className="absolute right-2 top-1/2 -translate-y-1/2 p-2 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-900 text-white disabled:text-gray-650 rounded-xl transition-all shadow cursor-pointer"
                >
                  <Send className="h-4 w-4" />
                </button>
              </form>
              <div className="text-center text-[10px] text-gray-700 mt-2">
                🔒 Inferences are locked locally on corporate network databases.
              </div>
            </div>
          </div>
        )}
      </div>

      {/* 3. Sliding Citations Sources Panel drawer (Right side) */}
      {activeCitations && (
        <div className="absolute md:relative inset-y-0 right-0 w-80 bg-[#0c0f17] border-l border-gray-900/60 z-20 flex flex-col shadow-2xl">
          <div className="p-4 border-b border-gray-900/60 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <BookOpen className="h-5 w-5 text-brand-400" />
              <span className="font-bold text-white text-sm">Grounded Sources</span>
            </div>
            <button
              onClick={() => setActiveCitations(null)}
              className="text-gray-500 hover:text-white text-xs border border-gray-850 hover:bg-gray-850 rounded-lg py-1 px-2.5 transition-colors cursor-pointer"
            >
              Close
            </button>
          </div>
          
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {activeCitations.map((citation, index) => (
              <div 
                key={index}
                className="p-4 rounded-xl bg-darkCard border border-gray-800/80 space-y-2 text-xs"
              >
                <div className="flex items-center justify-between text-[10px] font-semibold text-brand-300">
                  <span>Source Reference {citation.id}</span>
                  <span className="text-[10px] text-gray-550">Match: {Math.round((1 - citation.score/2) * 100)}%</span>
                </div>
                <div className="font-semibold text-white truncate" title={citation.filename}>
                  {citation.filename}
                </div>
                <div className="text-[10px] text-gray-550">
                  Page Number: {citation.page_number} | Index: {citation.chunk_index}
                </div>
                <div className="p-2.5 rounded bg-darkSurface border border-gray-900/60 text-gray-400 italic text-[11px] leading-relaxed">
                  "{citation.snippet}..."
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
