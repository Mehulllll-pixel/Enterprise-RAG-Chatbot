import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  FileText, Upload, Trash2, Plus, RefreshCw, Filter, 
  CheckCircle, AlertCircle, Loader2, Tag, Layers, Calendar, Eye, Database, Info, X
} from 'lucide-react';

interface DocumentItem {
  id: string;
  filename: string;
  department_id: string;
  owner_id: string;
  current_version: number;
  status: string; // PENDING, PROCESSING, COMPLETED, FAILED
  tags: string[];
  created_at: string;
  updated_at: string;
}

interface ChunkPreviewItem {
  index: number;
  page_number: number;
  text: string;
}

export const DocumentLibrary: React.FC = () => {
  const { user } = useAuth();
  
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Filter States
  const [statusFilter, setStatusFilter] = useState('');
  const [tagFilter, setTagFilter] = useState('');
  const [allTags, setAllTags] = useState<string[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  // Upload States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTags, setUploadTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // New Version States
  const [updatingDocId, setUpdatingDocId] = useState<string | null>(null);

  // Preview Modal States
  const [previewDoc, setPreviewDoc] = useState<DocumentItem | null>(null);
  const [previewChunks, setPreviewChunks] = useState<ChunkPreviewItem[]>([]);
  const [previewLoading, setPreviewLoading] = useState(false);

  const fetchDocuments = async () => {
    if (!user || !user.department_id) return;
    try {
      const url = `/api/v1/documents?department_id=${user.department_id}` +
        (statusFilter ? `&status=${statusFilter}` : '') +
        (tagFilter ? `&tag=${tagFilter}` : '');
      const response = await api.get(url);
      setDocuments(response);

      // Extract unique tags for tags filtering dropdown
      const tagsSet = new Set<string>();
      response.forEach((doc: DocumentItem) => {
        doc.tags.forEach(t => tagsSet.add(t));
      });
      setAllTags(Array.from(tagsSet));
    } catch (err: any) {
      setError(err.message || 'Failed to retrieve corporate document library.');
    } finally {
      setIsLoading(false);
    }
  };

  // Poll for document status updates if any are in PENDING or PROCESSING states
  useEffect(() => {
    fetchDocuments();
  }, [user, statusFilter, tagFilter]);

  useEffect(() => {
    const hasActiveJobs = documents.some(d => d.status === 'PENDING' || d.status === 'PROCESSING');
    if (!hasActiveJobs) return;

    const interval = setInterval(() => {
      fetchDocuments();
    }, 4500);

    return () => clearInterval(interval);
  }, [documents]);

  // Drag and drop handlers
  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      setUploadFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setUploadFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile || !user?.department_id) return;
    
    setIsUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const formData = new FormData();
      formData.append('file', uploadFile);
      formData.append('department_id', user.department_id);
      
      if (uploadTags) {
        const tagsArr = uploadTags.split(',').map(t => t.trim()).filter(Boolean);
        formData.append('tags_json', JSON.stringify(tagsArr));
      }

      await api.post('/api/v1/documents/upload', formData);
      setSuccess(`File "${uploadFile.name}" enqueued for parsing successfully.`);
      setUploadFile(null);
      setUploadTags('');
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchDocuments();
    } catch (err: any) {
      setError(err.message || 'File upload constraints validation failed.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this document? This will purge all text chunks and indexed vector embeddings.')) {
      return;
    }
    setError(null);
    setSuccess(null);
    try {
      await api.delete(`/api/v1/documents/${id}`);
      setSuccess('Document purged successfully.');
      fetchDocuments();
      if (previewDoc?.id === id) {
        setPreviewDoc(null);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to purge document.');
    }
  };

  const handleVersionSubmit = async (id: string, file: File) => {
    setUpdatingDocId(id);
    setError(null);
    setSuccess(null);
    try {
      const formData = new FormData();
      formData.append('file', file);

      await api.post(`/api/v1/documents/${id}/new-version`, formData);
      setSuccess(`New version submitted for processing.`);
      fetchDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to upload new document version.');
    } finally {
      setUpdatingDocId(null);
    }
  };

  const handleReindex = async (id: string) => {
    setError(null);
    setSuccess(null);
    try {
      await api.post(`/api/v1/documents/${id}/reindex`, {});
      setSuccess('Re-indexing job enqueued.');
      fetchDocuments();
    } catch (err: any) {
      setError(err.message || 'Failed to enqueue reindexing.');
    }
  };

  // Preview Chunks trigger
  const handlePreviewDoc = async (doc: DocumentItem) => {
    setPreviewDoc(doc);
    setPreviewChunks([]);
    setPreviewLoading(true);
    
    try {
      const chunks = await api.get(`/api/v1/documents/${doc.id}/chunks`);
      setPreviewChunks(chunks || []);
    } catch (err) {
      console.error(err);
    } finally {
      setPreviewLoading(false);
    }
  };

  // Helper formatting size
  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Status helper pills
  const renderStatusPill = (status: string) => {
    switch (status) {
      case 'COMPLETED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-[10px] font-semibold">
            <CheckCircle className="h-3 w-3" />
            <span>Indexed</span>
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-blue-500/10 border border-blue-500/20 text-blue-400 text-[10px] font-semibold">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Processing</span>
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-[10px] font-semibold">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Pending</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-red-500/10 border border-red-500/20 text-red-400 text-[10px] font-semibold">
            <AlertCircle className="h-3 w-3" />
            <span>Failed</span>
          </span>
        );
      default:
        return null;
    }
  };

  const isUploaderRole = user?.role_id === 'ADMIN' || user?.role_id === 'MANAGER' || user?.role_id === 'ENGINEER';
  
  // Calculate dynamic stats
  const totalDocs = documents.length;
  const indexedDocs = documents.filter(d => d.status === 'COMPLETED').length;
  const processingDocs = documents.filter(d => d.status === 'PROCESSING' || d.status === 'PENDING').length;
  const failedDocs = documents.filter(d => d.status === 'FAILED').length;

  // Local Search filtering
  const filteredDocs = documents.filter(doc => 
    doc.filename.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="container mx-auto px-4 py-8 max-w-7xl font-sans text-white">
      
      {/* Title Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3.5">
          <div className="p-3 bg-brand-500/10 border border-brand-500/20 rounded-2xl text-brand-400 shadow-inner">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-extrabold text-white tracking-tight">Corporate Document Library</h1>
            <p className="text-gray-400 text-xs mt-0.5">
              Secure Knowledge Base Scope: <span className="text-brand-300 font-semibold">{user?.department_name || 'System Scoped'}</span>
            </p>
          </div>
        </div>
        <button
          onClick={fetchDocuments}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-850 hover:border-gray-700 text-gray-300 transition-all text-xs cursor-pointer font-semibold"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          <span>Sync Repository</span>
        </button>
      </div>

      {/* Corporate Library Statistics Summary Headers */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <div className="glass-panel p-4 rounded-2xl border border-gray-900/60 flex items-center gap-4">
          <div className="p-2.5 bg-brand-500/5 rounded-xl border border-brand-500/10 text-brand-400 shrink-0">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Total Files</div>
            <div className="text-xl font-extrabold text-white mt-0.5">{totalDocs}</div>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-gray-900/60 flex items-center gap-4">
          <div className="p-2.5 bg-emerald-500/5 rounded-xl border border-emerald-500/10 text-emerald-400 shrink-0">
            <CheckCircle className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Indexed Chunks</div>
            <div className="text-xl font-extrabold text-white mt-0.5">{indexedDocs}</div>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-gray-900/60 flex items-center gap-4">
          <div className="p-2.5 bg-blue-500/5 rounded-xl border border-blue-500/10 text-blue-400 shrink-0">
            <Loader2 className="h-5 w-5 animate-pulse" />
          </div>
          <div>
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Processing</div>
            <div className="text-xl font-extrabold text-white mt-0.5">{processingDocs}</div>
          </div>
        </div>

        <div className="glass-panel p-4 rounded-2xl border border-gray-900/60 flex items-center gap-4">
          <div className="p-2.5 bg-red-500/5 rounded-xl border border-red-500/10 text-red-400 shrink-0">
            <AlertCircle className="h-5 w-5" />
          </div>
          <div>
            <div className="text-[10px] text-gray-500 font-bold uppercase tracking-wider">Failed Indexes</div>
            <div className="text-xl font-extrabold text-white mt-0.5">{failedDocs}</div>
          </div>
        </div>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm animate-pulse">
          <AlertCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{error}</span>
        </div>
      )}

      {success && (
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-emerald-500/10 border border-emerald-500/20 p-4 text-emerald-400 text-sm">
          <CheckCircle className="h-5 w-5 shrink-0 mt-0.5" />
          <span>{success}</span>
        </div>
      )}

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Document Ingestion Panel (Left column) */}
        {isUploaderRole && (
          <div className="lg:col-span-1 space-y-6">
            <div className="glass-panel rounded-2xl p-6 border border-gray-900/60 shadow-lg relative">
              <h2 className="text-sm font-bold text-white uppercase tracking-wider mb-4 flex items-center gap-2">
                <Upload className="h-4.5 w-4.5 text-brand-400" />
                <span>Ingest Document</span>
              </h2>

              <form onSubmit={handleUploadSubmit} className="space-y-4">
                {/* Drag and Drop Box */}
                <div
                  onDragEnter={handleDrag}
                  onDragOver={handleDrag}
                  onDragLeave={handleDrag}
                  onDrop={handleDrop}
                  onClick={() => fileInputRef.current?.click()}
                  className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px] ${
                    dragActive 
                      ? 'border-brand-500 bg-brand-500/5 scale-[0.98]' 
                      : uploadFile 
                        ? 'border-emerald-500/40 bg-emerald-500/5'
                        : 'border-gray-800 hover:border-gray-700 bg-darkSurface/50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFileChange}
                    disabled={isUploading}
                  />

                  {uploadFile ? (
                    <>
                      <FileText className="h-10 w-10 text-emerald-400 mb-2 scale-up animate" />
                      <p className="text-white text-xs font-semibold truncate max-w-[200px]">{uploadFile.name}</p>
                      <p className="text-gray-500 text-[10px] mt-1">{formatSize(uploadFile.size)}</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-650 mb-2" />
                      <p className="text-gray-300 text-xs font-semibold">Click or drag document here</p>
                      <p className="text-gray-500 text-[10px] mt-1">PDF, DOCX, TXT, MD (Max 15MB)</p>
                    </>
                  )}
                </div>

                {/* Ingestion active loading progress bar */}
                {isUploading && (
                  <div className="space-y-2 py-2">
                    <div className="flex items-center justify-between text-[10px] font-bold uppercase tracking-wider text-brand-300">
                      <span>Uploading to parser...</span>
                      <span className="animate-pulse text-brand-400">Processing</span>
                    </div>
                    <div className="w-full h-1.5 bg-gray-950 rounded-full overflow-hidden border border-gray-900 shadow-inner">
                      <div className="h-full bg-brand-500 rounded-full animate-pulse" style={{ width: '70%' }}></div>
                    </div>
                  </div>
                )}

                {/* Tags input */}
                <div>
                  <label className="block text-[10px] font-bold text-gray-400 mb-2 uppercase tracking-wider">Document Tags (Comma-separated)</label>
                  <div className="relative">
                    <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-gray-600" />
                    <input
                      type="text"
                      className="w-full pl-9 pr-4 py-2 bg-darkSurface border border-gray-800 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-xs shadow-inner"
                      placeholder="e.g. HR, Policy, 2026"
                      value={uploadTags}
                      onChange={(e) => setUploadTags(e.target.value)}
                      disabled={isUploading}
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={isUploading || !uploadFile}
                  className="w-full py-2.5 px-4 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-900 disabled:text-gray-600 text-white font-semibold rounded-xl flex items-center justify-center gap-2 transition-all shadow-md text-xs cursor-pointer"
                >
                  {isUploading ? (
                    <>
                      <Loader2 className="h-4 w-4 animate-spin" />
                      <span>Ingesting File...</span>
                    </>
                  ) : (
                    <span>Submit to Index</span>
                  )}
                </button>
              </form>
            </div>
          </div>
        )}

        {/* Documents Directory List (Right columns) */}
        <div className={isUploaderRole ? 'lg:col-span-2 space-y-6' : 'lg:col-span-3 space-y-6'}>
          {/* Search and Filters Bar */}
          <div className="glass-panel rounded-2xl p-4 border border-gray-900/60 flex flex-col md:flex-row gap-4 items-center justify-between text-xs">
            
            {/* Search Input */}
            <div className="w-full md:w-72 relative">
              <input
                type="text"
                className="w-full bg-darkSurface border border-gray-800 text-white rounded-xl py-2 pl-3.5 pr-8 focus:outline-none focus:border-brand-500 text-xs"
                placeholder="Search filenames..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
              />
            </div>

            {/* Filter Dropdowns */}
            <div className="flex items-center gap-3 w-full md:w-auto justify-end">
              <span className="text-gray-500 font-bold uppercase tracking-wider text-[10px] flex items-center gap-1">
                <Filter className="h-3.5 w-3.5" />
                <span>Filters:</span>
              </span>

              {/* Status Filter */}
              <select
                className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-[11px] focus:ring-1 focus:ring-brand-500"
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
              >
                <option value="">All Statuses</option>
                <option value="COMPLETED">Indexed</option>
                <option value="PROCESSING">Processing</option>
                <option value="PENDING">Pending</option>
                <option value="FAILED">Failed</option>
              </select>

              {/* Tag Filter */}
              <select
                className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-[11px] focus:ring-1 focus:ring-brand-500"
                value={tagFilter}
                onChange={(e) => setTagFilter(e.target.value)}
              >
                <option value="">All Tags</option>
                {allTags.map(tag => (
                  <option key={tag} value={tag}>{tag}</option>
                ))}
              </select>
            </div>
          </div>

          {/* Table Directory Card */}
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
                <span className="text-gray-400 text-sm font-semibold">Loading document directory...</span>
              </div>
            </div>
          ) : filteredDocs.length === 0 ? (
            <div className="glass-panel rounded-3xl p-12 text-center text-gray-500 border border-gray-900/60">
              <FileText className="h-12 w-12 mx-auto text-gray-800 mb-3" />
              <p className="font-semibold text-gray-450 text-base">No Matching Documents</p>
              <p className="text-xs text-gray-550 mt-1 max-w-sm mx-auto">Upload policy guides, corporate guidelines, or manuals to populate the directory scope.</p>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl overflow-hidden shadow-lg border border-gray-900/60">
              <div className="divide-y divide-gray-900/40">
                {filteredDocs.map((doc) => (
                  <div key={doc.id} className="p-4 hover:bg-darkSurface/10 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4">
                    
                    {/* Document Info */}
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="p-2.5 bg-brand-500/5 border border-brand-500/10 rounded-xl text-brand-400 shrink-0 mt-0.5 shadow-inner">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 
                            onClick={() => handlePreviewDoc(doc)}
                            className="text-sm font-semibold text-white hover:text-brand-300 transition-colors cursor-pointer truncate max-w-xs md:max-w-md"
                            title="Click to preview indexed text chunks"
                          >
                            {doc.filename}
                          </h3>
                          {renderStatusPill(doc.status)}
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] text-gray-500 mt-1">
                          <span className="flex items-center gap-1">
                            <Layers className="h-3.5 w-3.5 text-gray-700" />
                            <span>Version {doc.current_version}</span>
                          </span>
                          <span className="flex items-center gap-1">
                            <Calendar className="h-3.5 w-3.5 text-gray-700" />
                            <span>
                              {new Date(doc.updated_at).toLocaleDateString(undefined, {
                                month: 'short',
                                day: 'numeric',
                                hour: '2-digit',
                                minute: '2-digit'
                              })}
                            </span>
                          </span>
                        </div>

                        {/* Tags list */}
                        {doc.tags.length > 0 && (
                          <div className="flex flex-wrap gap-1.5 mt-2">
                            {doc.tags.map(t => (
                              <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-950 border border-gray-900 text-gray-500 text-[9px] font-bold tracking-wider uppercase">
                                <Tag className="h-2 w-2 text-gray-700" />
                                <span>{t}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-2 shrink-0">
                      
                      {/* Preview Button */}
                      <button
                        onClick={() => handlePreviewDoc(doc)}
                        className="p-2 bg-gray-900 hover:bg-gray-850 border border-gray-800 text-gray-400 hover:text-white rounded-xl transition-all cursor-pointer"
                        title="Preview indexed text chunks"
                      >
                        <Eye className="h-3.5 w-3.5" />
                      </button>

                      {isUploaderRole && (
                        <>
                          {/* File input for new version */}
                          <input
                            type="file"
                            className="hidden"
                            accept=".pdf,.docx,.txt,.md"
                            id={`version-file-${doc.id}`}
                            onChange={(e) => {
                              if (e.target.files && e.target.files[0]) {
                                handleVersionSubmit(doc.id, e.target.files[0]);
                              }
                            }}
                          />
                          <button
                            onClick={() => document.getElementById(`version-file-${doc.id}`)?.click()}
                            disabled={updatingDocId === doc.id || doc.status === 'PROCESSING'}
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 text-gray-300 hover:text-white rounded-xl text-xs transition-colors disabled:opacity-50 cursor-pointer font-semibold"
                            title="Upload new file version"
                          >
                            {updatingDocId === doc.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Plus className="h-3.5 w-3.5" />
                            )}
                            <span>Update</span>
                          </button>

                          {/* Reindex Button */}
                          <button
                            onClick={() => handleReindex(doc.id)}
                            disabled={doc.status === 'PROCESSING'}
                            className="p-2 bg-gray-900 hover:bg-gray-850 border border-gray-800 text-gray-400 hover:text-white rounded-xl transition-all disabled:opacity-50 cursor-pointer"
                            title="Reindex Document"
                          >
                            <RefreshCw className="h-3.5 w-3.5" />
                          </button>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-2 bg-red-950/20 hover:bg-red-950/30 border border-red-900/20 text-red-400 hover:text-red-300 rounded-xl transition-all cursor-pointer"
                            title="Purge Document"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* 4. Interactive Chunks Preview Modal Dialog overlay */}
      {previewDoc && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-center justify-center p-4">
          <div className="bg-[#0b0e14] border border-gray-900 max-w-3xl w-full max-h-[85vh] rounded-3xl overflow-hidden flex flex-col shadow-2xl relative scale-up animate">
            
            {/* Modal Header */}
            <div className="p-5 border-b border-gray-900 flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <div className="p-2 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-400 shrink-0">
                  <Database className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="font-extrabold text-white text-base truncate max-w-md">{previewDoc.filename}</h3>
                  <span className="text-[10px] text-gray-500 font-bold uppercase tracking-wider block mt-0.5">Vector Chunks Preview Console</span>
                </div>
              </div>
              <button
                onClick={() => setPreviewDoc(null)}
                className="p-1.5 border border-gray-850 hover:bg-gray-850 text-gray-500 hover:text-white rounded-xl transition-colors cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 overflow-y-auto p-6 space-y-4">
              {/* Document metadata info panel */}
              <div className="p-4 rounded-2xl bg-darkCard border border-gray-900/60 grid grid-cols-2 md:grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-gray-550 block font-medium">Document ID</span>
                  <span className="font-semibold text-white block mt-0.5 font-mono text-[10px] truncate" title={previewDoc.id}>
                    {previewDoc.id}
                  </span>
                </div>
                <div>
                  <span className="text-gray-550 block font-medium">Active Version</span>
                  <span className="font-semibold text-white block mt-0.5">
                    Version {previewDoc.current_version}
                  </span>
                </div>
                <div>
                  <span className="text-gray-550 block font-medium">Indexing Status</span>
                  <span className="block mt-0.5">{renderStatusPill(previewDoc.status)}</span>
                </div>
                <div>
                  <span className="text-gray-550 block font-medium">Indexed Date</span>
                  <span className="font-semibold text-white block mt-0.5">
                    {new Date(previewDoc.created_at).toLocaleDateString()}
                  </span>
                </div>
              </div>

              {/* Chunks feed */}
              <div className="space-y-3">
                <h4 className="text-[10px] text-gray-500 font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <Info className="h-3.5 w-3.5 text-gray-650" />
                  <span>Grounding Text Fragments ({previewChunks.length})</span>
                </h4>
                
                {previewLoading ? (
                  <div className="flex flex-col items-center justify-center py-12 gap-2 text-xs text-gray-500">
                    <Loader2 className="h-6 w-6 animate-spin text-brand-500" />
                    <span>Retrieving index vector chunks from SQLite...</span>
                  </div>
                ) : previewChunks.length === 0 ? (
                  <div className="text-center py-8 text-gray-600 text-xs">
                    No text chunks indexed for this document. Try re-indexing.
                  </div>
                ) : (
                  <div className="space-y-3.5">
                    {previewChunks.map((chunk) => (
                      <div 
                        key={chunk.index}
                        className="p-4 rounded-xl bg-darkSurface border border-gray-900/60 space-y-2 text-xs"
                      >
                        <div className="flex items-center justify-between text-[9px] font-bold tracking-wider text-brand-350 uppercase">
                          <span>Chunk Index #{chunk.index + 1}</span>
                          {chunk.page_number !== null && (
                            <span>Page {chunk.page_number}</span>
                          )}
                        </div>
                        <p className="text-gray-300 leading-relaxed font-sans select-text">
                          {chunk.text}
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Modal Footer */}
            <div className="p-4 bg-[#0c0f17] border-t border-gray-900 text-right">
              <button
                onClick={() => setPreviewDoc(null)}
                className="px-5 py-2 bg-brand-500 hover:bg-brand-600 text-white font-semibold rounded-xl text-xs transition-colors cursor-pointer"
              >
                Close Preview
              </button>
            </div>

          </div>
        </div>
      )}

    </div>
  );
};
