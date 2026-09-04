import React, { useState, useEffect } from 'react';
import { UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, BookOpen, Layers, Search, Sparkles } from 'lucide-react';
import { uploadContextFile, getContextDocuments } from '../api/client';

export default function KnowledgeBaseView() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [successMsg, setSuccessMsg] = useState('');
  const [dragActive, setDragActive] = useState(false);

  useEffect(() => {
    fetchDocuments();
  }, []);

  const fetchDocuments = async () => {
    try {
      const docs = await getContextDocuments();
      setDocuments(docs || []);
    } catch (err) {
      console.error('Failed to load context documents:', err);
    }
  };

  const handleFile = async (file) => {
    if (!file) return;

    setLoading(true);
    setError(null);
    setSuccessMsg('');

    try {
      const res = await uploadContextFile(file);
      setSuccessMsg(`Successfully indexed "${res.filename}" into FAISS dense vector store & BM25 index (${res.chunks_created} semantic chunks).`);
      fetchDocuments();
    } catch (err) {
      console.error('Upload Context Error:', err);
      setError(err.response?.data?.detail || 'Failed to upload business context document.');
    } finally {
      setLoading(false);
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  return (
    <div className="kb-container">
      {/* Knowledge Base Header */}
      <div className="kb-header">
        <div className="kb-title-box">
          <BookOpen className="icon-large text-purple" />
          <div>
            <h2 className="kb-title">Business Knowledge Base (Hybrid RAG)</h2>
            <p className="kb-subtitle">
              Upload business glossaries, policy documentation, SLA rules, or prior reports (.pdf, .txt, .md).
              DataSense indexes text into <strong>FAISS vector embeddings</strong> and <strong>BM25 sparse search</strong> for grounded AI answers.
            </p>
          </div>
        </div>
      </div>

      <div className="kb-grid-layout">
        {/* Upload Card */}
        <div className="kb-card upload-card">
          <h3 className="card-heading">
            <UploadCloud className="icon-small text-purple" /> Add Knowledge Document
          </h3>

          <div
            className={`dropzone ${dragActive ? 'active' : ''} ${loading ? 'disabled' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
          >
            <input
              type="file"
              id="kb-file-input"
              accept=".pdf,.txt,.md"
              onChange={(e) => e.target.files?.[0] && handleFile(e.target.files[0])}
              disabled={loading}
              className="file-input"
            />
            <label htmlFor="kb-file-input" className="dropzone-label">
              {loading ? (
                <div className="upload-state">
                  <Loader2 className="animate-spin icon-large text-purple" />
                  <p className="state-title">Embedding text & indexing FAISS + BM25...</p>
                  <p className="state-subtitle">Generating dense vector embeddings with BAAI/bge-small-en-v1.5</p>
                </div>
              ) : (
                <div className="upload-state">
                  <div className="icon-wrapper purple-glow">
                    <UploadCloud className="icon-large text-purple" />
                  </div>
                  <p className="state-title">Click to upload or drag & drop</p>
                  <p className="state-subtitle">Supports PDF documents (.pdf), Text files (.txt), and Markdown (.md)</p>
                </div>
              )}
            </label>
          </div>

          {error && (
            <div className="error-banner margin-top">
              <AlertCircle className="icon-small" />
              <span>{error}</span>
            </div>
          )}

          {successMsg && (
            <div className="success-banner margin-top">
              <CheckCircle2 className="icon-small text-emerald" />
              <span>{successMsg}</span>
            </div>
          )}
        </div>

        {/* Indexed Knowledge Documents Card */}
        <div className="kb-card docs-card">
          <div className="flex-between margin-bottom">
            <h3 className="card-heading">
              <Layers className="icon-small text-blue" /> Active Knowledge Base ({documents.length})
            </h3>
            <span className="kb-badge-pill">
              {documents.reduce((acc, d) => acc + (d.chunk_count || 0), 0)} Total Chunks Indexed
            </span>
          </div>

          {documents.length === 0 ? (
            <div className="empty-kb-state">
              <FileText className="icon-large text-gray" />
              <p className="empty-title">No business context documents uploaded yet</p>
              <p className="empty-subtitle">
                Upload a glossary or policy file above (such as <code>superstore_context.txt</code> in <code>backend/sample_data/</code>).
              </p>
            </div>
          ) : (
            <div className="indexed-docs-grid">
              {documents.map((doc) => (
                <div key={doc.doc_id} className="indexed-doc-card">
                  <div className="doc-card-header">
                    <div className="doc-icon-wrapper">
                      <FileText className="icon-medium text-purple" />
                    </div>
                    <div className="doc-meta">
                      <h4 className="doc-title">{doc.filename}</h4>
                      <span className="doc-chunks-count">{doc.chunk_count} semantic chunks indexed</span>
                    </div>
                  </div>
                  <div className="doc-card-footer">
                    <span className="status-indicator">
                      <CheckCircle2 className="icon-tiny text-emerald" /> Active in RAG Index
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
