import React, { useState, useEffect, useRef } from 'react';
import { useAuth } from '../context/AuthContext';
import { api } from '../services/api';
import { 
  FileText, Upload, Trash2, Plus, RefreshCw, Filter, 
  CheckCircle, AlertCircle, Loader2, Tag, Layers, Calendar 
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

  // Upload States
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadTags, setUploadTags] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // New Version States
  const [updatingDocId, setUpdatingDocId] = useState<string | null>(null);

  const fetchDocuments = async () => {
    if (!user || !user.department_id) return;
    setError(null);
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
    }, 4000);

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
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium">
            <CheckCircle className="h-3.5 w-3.5" />
            <span>Indexed</span>
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-medium">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Processing</span>
          </span>
        );
      case 'PENDING':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 text-xs font-medium">
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
            <span>Pending</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-500/10 border border-red-500/20 text-red-400 text-xs font-medium">
            <AlertCircle className="h-3.5 w-3.5" />
            <span>Failed</span>
          </span>
        );
      default:
        return null;
    }
  };

  const isUploaderRole = user?.role_id === 'ADMIN' || user?.role_id === 'MANAGER' || user?.role_id === 'ENGINEER';

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Title */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div className="flex items-center gap-3">
          <div className="p-2.5 bg-brand-500/10 border border-brand-500/20 rounded-xl text-brand-400">
            <FileText className="h-6 w-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white">Department Document Library</h1>
            <p className="text-gray-400 text-sm">
              Scope: <span className="text-accent-teal font-medium">{user?.department_name || 'No scoping'}</span>
            </p>
          </div>
        </div>
        <button
          onClick={fetchDocuments}
          className="flex items-center justify-center gap-2 px-4 py-2.5 bg-gray-900 border border-gray-800 rounded-xl hover:bg-gray-800 text-gray-300 transition-colors text-sm"
        >
          <RefreshCw className="h-4 w-4" />
          <span>Refresh List</span>
        </button>
      </div>

      {/* Alerts */}
      {error && (
        <div className="mb-6 flex items-start gap-3 rounded-xl bg-red-500/10 border border-red-500/20 p-4 text-red-400 text-sm">
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
            <div className="glass-panel rounded-2xl p-6 shadow-lg">
              <h2 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
                <Upload className="h-5 w-5 text-brand-400" />
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
                  className={`border-2 border-dashed rounded-xl p-6 text-center cursor-pointer transition-all flex flex-col items-center justify-center min-h-[160px] ${
                    dragActive 
                      ? 'border-brand-500 bg-brand-500/5' 
                      : uploadFile 
                        ? 'border-emerald-500/50 bg-emerald-500/5'
                        : 'border-gray-800 hover:border-gray-700 bg-darkSurface/50'
                  }`}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    className="hidden"
                    accept=".pdf,.docx,.txt,.md"
                    onChange={handleFileChange}
                  />

                  {uploadFile ? (
                    <>
                      <FileText className="h-8 w-8 text-emerald-400 mb-2" />
                      <p className="text-white text-sm font-medium truncate max-w-xs">{uploadFile.name}</p>
                      <p className="text-gray-500 text-xs mt-1">{formatSize(uploadFile.size)}</p>
                    </>
                  ) : (
                    <>
                      <Upload className="h-8 w-8 text-gray-500 mb-2" />
                      <p className="text-gray-300 text-sm font-medium">Click or Drag File</p>
                      <p className="text-gray-500 text-xs mt-1">PDF, DOCX, TXT, MD (Max 15MB)</p>
                    </>
                  )}
                </div>

                {/* Tags input */}
                <div>
                  <label className="block text-xs font-medium text-gray-400 mb-2 uppercase tracking-wider">Document Tags (Comma-separated)</label>
                  <div className="relative">
                    <Tag className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-500" />
                    <input
                      type="text"
                      className="w-full pl-9 pr-4 py-2.5 bg-darkSurface border border-gray-800 rounded-xl text-white placeholder-gray-600 focus:outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 text-sm"
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
                  className="w-full py-2.5 px-4 bg-brand-500 hover:bg-brand-600 disabled:bg-gray-900 disabled:text-gray-600 text-white font-medium rounded-xl flex items-center justify-center gap-2 transition-all shadow-md"
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
          {/* Filters Bar */}
          <div className="glass-panel rounded-xl p-4 flex flex-wrap items-center gap-4 text-sm">
            <span className="text-gray-400 font-medium flex items-center gap-1.5">
              <Filter className="h-4 w-4" />
              <span>Filters:</span>
            </span>

            {/* Status Filter */}
            <select
              className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-xs focus:ring-1 focus:ring-brand-500"
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
              className="bg-darkSurface border border-gray-800 text-gray-300 rounded-lg py-1.5 px-3 focus:outline-none focus:border-brand-500 text-xs focus:ring-1 focus:ring-brand-500"
              value={tagFilter}
              onChange={(e) => setTagFilter(e.target.value)}
            >
              <option value="">All Tags</option>
              {allTags.map(tag => (
                <option key={tag} value={tag}>{tag}</option>
              ))}
            </select>
          </div>

          {/* Table Directory Card */}
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <div className="flex flex-col items-center gap-3">
                <Loader2 className="h-10 w-10 animate-spin text-brand-500" />
                <span className="text-gray-400 text-sm">Loading document directory...</span>
              </div>
            </div>
          ) : documents.length === 0 ? (
            <div className="glass-panel rounded-2xl p-12 text-center text-gray-500">
              <FileText className="h-12 w-12 mx-auto text-gray-700 mb-3" />
              <p className="font-medium text-gray-300 text-base">No Documents Indexed</p>
              <p className="text-sm text-gray-500 mt-1">Upload company policy files, TXT, MD or DOCX guides to start RAG questioning.</p>
            </div>
          ) : (
            <div className="glass-panel rounded-2xl overflow-hidden shadow-lg border border-gray-800/40">
              <div className="divide-y divide-gray-800/50">
                {documents.map((doc) => (
                  <div key={doc.id} className="p-5 hover:bg-darkSurface/20 transition-colors flex flex-col md:flex-row md:items-center justify-between gap-4">
                    
                    {/* Document Info */}
                    <div className="flex items-start gap-3 min-w-0">
                      <div className="p-2 bg-brand-500/5 border border-brand-500/10 rounded-lg text-brand-400 shrink-0 mt-0.5">
                        <FileText className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="text-sm font-semibold text-white truncate max-w-xs md:max-w-md">{doc.filename}</h3>
                          {renderStatusPill(doc.status)}
                        </div>
                        
                        <div className="flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500 mt-1.5">
                          <span className="flex items-center gap-1.5">
                            <Layers className="h-3.5 w-3.5 text-gray-600" />
                            <span>Version {doc.current_version}</span>
                          </span>
                          <span className="flex items-center gap-1.5">
                            <Calendar className="h-3.5 w-3.5 text-gray-600" />
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
                              <span key={t} className="inline-flex items-center gap-1 px-2 py-0.5 rounded bg-gray-900 border border-gray-800 text-gray-400 text-[10px] font-medium">
                                <Tag className="h-2.5 w-2.5 text-gray-650" />
                                <span>{t}</span>
                              </span>
                            ))}
                          </div>
                        )}
                      </div>
                    </div>

                    {/* Action buttons */}
                    <div className="flex items-center gap-2 shrink-0">
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
                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 text-gray-300 hover:text-white rounded-lg text-xs transition-colors disabled:opacity-50"
                            title="Upload new file version"
                          >
                            {updatingDocId === doc.id ? (
                              <Loader2 className="h-3.5 w-3.5 animate-spin" />
                            ) : (
                              <Plus className="h-3.5 w-3.5" />
                            )}
                            <span>New Version</span>
                          </button>

                          {/* Reindex Button */}
                          <button
                            onClick={() => handleReindex(doc.id)}
                            disabled={doc.status === 'PROCESSING'}
                            className="p-1.5 bg-gray-900 hover:bg-gray-850 border border-gray-800 text-gray-400 hover:text-white rounded-lg transition-colors disabled:opacity-50"
                            title="Reindex Document"
                          >
                            <RefreshCw className="h-3.5 w-3.5" />
                          </button>

                          {/* Delete Button */}
                          <button
                            onClick={() => handleDelete(doc.id)}
                            className="p-1.5 bg-red-950/20 hover:bg-red-950/40 border border-red-900/30 text-red-400 hover:text-red-300 rounded-lg transition-colors"
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
    </div>
  );
};
