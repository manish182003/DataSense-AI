import React, { useState } from 'react';
import { Upload, FileText, AlertCircle, Loader2 } from 'lucide-react';
import { uploadDataset } from '../api/client';

export default function DatasetUpload({ onUploadSuccess }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true);
    setError(null);

    try {
      const data = await uploadDataset(file);
      onUploadSuccess(data);
    } catch (err) {
      console.error('Upload Error:', err);
      setError(err.response?.data?.detail || 'Failed to upload dataset. Please check file format.');
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

  const handleChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="upload-container">
      <div 
        className={`dropzone ${dragActive ? 'active' : ''} ${loading ? 'disabled' : ''}`}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input 
          type="file" 
          id="file-upload-input" 
          accept=".csv,.xlsx,.xls,.json" 
          onChange={handleChange}
          disabled={loading}
          className="file-input"
        />
        <label htmlFor="file-upload-input" className="dropzone-label">
          {loading ? (
            <div className="upload-state">
              <Loader2 className="animate-spin icon-large text-blue" />
              <p className="state-title">Ingesting & Inferring Schema into DuckDB...</p>
              <p className="state-subtitle">Parsing data types, building summary stats & profiles</p>
            </div>
          ) : (
            <div className="upload-state">
              <div className="icon-wrapper">
                <Upload className="icon-large text-blue" />
              </div>
              <p className="state-title">Click to upload or drag & drop</p>
              <p className="state-subtitle">Supports CSV, Excel (.xlsx, .xls) and JSON datasets</p>
            </div>
          )}
        </label>
      </div>

      {error && (
        <div className="error-banner">
          <AlertCircle className="icon-small" />
          <span>{error}</span>
        </div>
      )}
    </div>
  );
}
