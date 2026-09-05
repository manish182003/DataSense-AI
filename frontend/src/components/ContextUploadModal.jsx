import React, { useState, useEffect } from 'react';
import { X, UploadCloud, FileText, CheckCircle2, AlertCircle, Loader2, BookOpen, RotateCcw } from 'lucide-react';
import { uploadContextFile, getContextDocuments } from '../api/client';

export default function ContextUploadModal({ isOpen, onClose }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [successMsg, setSuccessMsg] = useState('');

  useEffect(() => {
    if (isOpen) {
      fetchDocuments();
    }
  }, [isOpen]);

  const fetchDocuments = async () => {
    try {
      const docs = await getContextDocuments();
      setDocuments(docs || []);
    } catch (err) {
      console.error('Failed to load context documents:', err);
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setLoading(true);
    setProgress(0);
    setFileName(file.name);
    setError(null);
    setSuccessMsg('');

    try {
      const res = await uploadContextFile(file, (percent) => {
        setProgress(percent);
      });
      setSuccessMsg(`Successfully indexed "${res.filename}" (${res.chunks_created} semantic chunks).`);
      fetchDocuments();
    } catch (err) {
      console.error('Upload Context Error:', err);
      setError(err.message || 'Failed to upload business context document.');
    } finally {
      setLoading(false);
    }
  };

  const resetUpload = () => {
    setError(null);
    setLoading(false);
    setProgress(0);
    setFileName('');
  };

  if (!isOpen) return null;

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div className="modal-title-group">
            <BookOpen className="icon-medium text-purple" />
            <div>
              <h3 className="modal-title">Business Context Knowledge Base</h3>
              <p className="modal-subtitle">Upload glossaries, schema documentation, or policy rules (.pdf, .txt, .md)</p>
            </div>
          </div>
          <button className="modal-close-btn" onClick={onClose}>
            <X className="icon-small" />
          </button>
        </div>

        <div className="modal-body">
          {/* File Upload Zone */}
          <div className="context-upload-box">
            <input
              type="file"
              id="context-file-input"
              accept=".pdf,.txt,.md"
              onChange={handleFileUpload}
              disabled={loading}
              className="file-input"
            />
            <label htmlFor="context-file-input" className="context-drop-label">
              {loading ? (
                <div className="upload-state flex-center">
                  <Loader2 className="animate-spin icon-medium text-purple" />
                  <span>
                    {progress < 100 
                      ? `Uploading "${fileName}" (${progress}%)...` 
                      : `Embedding text & indexing FAISS + BM25...`}
                  </span>
                  <div className="progress-bar-container margin-top-sm">
                    <div 
                      className="progress-bar-fill purple-fill" 
                      style={{ width: `${Math.max(progress, 5)}%` }}
                    ></div>
                  </div>
                </div>
              ) : (
                <div className="flex-center">
                  <UploadCloud className="icon-medium text-purple" />
                  <span>Click to upload business document (.pdf, .txt, .md)</span>
                </div>
              )}
            </label>
          </div>

          {error && (
            <div className="error-banner margin-top">
              <div className="error-content">
                <AlertCircle className="icon-small" />
                <span>{error}</span>
              </div>
              <button className="btn-retry-upload" onClick={resetUpload}>
                <RotateCcw className="icon-tiny inline-icon" /> Try Again
              </button>
            </div>
          )}

          {successMsg && (
            <div className="success-banner margin-top">
              <CheckCircle2 className="icon-small text-emerald" />
              <span>{successMsg}</span>
            </div>
          )}

          {/* Active Context Documents List */}
          <div className="documents-section">
            <h4 className="sub-title">Indexed Context Documents</h4>
            {documents.length === 0 ? (
              <div className="empty-docs-state">
                <FileText className="icon-medium text-gray" />
                <p>No business context documents uploaded yet.</p>
              </div>
            ) : (
              <div className="docs-list">
                {documents.map((doc) => (
                  <div key={doc.doc_id} className="doc-item">
                    <div className="doc-info">
                      <FileText className="icon-small text-purple" />
                      <span className="doc-name">{doc.filename}</span>
                    </div>
                    <div className="doc-badge">
                      {doc.chunk_count} chunks indexed
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        <div className="modal-footer">
          <button className="btn-primary" onClick={onClose}>
            Done
          </button>
        </div>
      </div>
    </div>
  );
}
