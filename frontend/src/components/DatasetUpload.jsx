import React, { useState } from 'react';
import { Upload, FileText, AlertCircle, Loader2, RotateCcw } from 'lucide-react';
import { uploadDataset } from '../api/client';

export default function DatasetUpload({ onUploadSuccess }) {
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [fileName, setFileName] = useState('');
  const [error, setError] = useState(null);
  const [dragActive, setDragActive] = useState(false);

  const handleFile = async (file) => {
    if (!file) return;
    setLoading(true);
    setProgress(0);
    setFileName(file.name);
    setError(null);

    try {
      const data = await uploadDataset(file, (percent) => {
        setProgress(percent);
      });
      onUploadSuccess(data);
    } catch (err) {
      console.error('Upload Error:', err);
      setError(err.message || 'Failed to upload dataset. Please check file format and server connection.');
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

  const resetUpload = () => {
    setError(null);
    setLoading(false);
    setProgress(0);
    setFileName('');
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
              <div className="upload-progress-info">
                <p className="state-title">
                  {progress < 100 
                    ? `Uploading "${fileName}" (${progress}%)` 
                    : `Ingesting into DuckDB & profiling summary stats...`}
                </p>
                <p className="state-subtitle">
                  {progress < 100 
                    ? 'Transferring file payload to DataSense engine' 
                    : 'Inferring schema, calculating column distributions & KPI summaries'}
                </p>
              </div>

              <div className="progress-bar-container">
                <div 
                  className="progress-bar-fill" 
                  style={{ width: `${Math.max(progress, 5)}%` }}
                ></div>
              </div>
            </div>
          ) : (
            <div className="upload-state">
              <div className="icon-wrapper">
                <Upload className="icon-large text-blue" />
              </div>
              <p className="state-title">Click to upload or drag & drop</p>
              <p className="state-subtitle">Supports CSV, Excel (.xlsx, .xls) and JSON datasets (up to 300,000+ rows)</p>
            </div>
          )}
        </label>
      </div>

      {error && (
        <div className="error-banner">
          <div className="error-content">
            <AlertCircle className="icon-small" />
            <span>{error}</span>
          </div>
          <button className="btn-retry-upload" onClick={resetUpload}>
            <RotateCcw className="icon-tiny inline-icon" /> Try Again
          </button>
        </div>
      )}
    </div>
  );
}
