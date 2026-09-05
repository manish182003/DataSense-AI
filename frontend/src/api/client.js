/**
 * API Client Service
 * Handles HTTP requests to the FastAPI DataSense backend endpoints.
 * Automatically adapts between local development (http://localhost:8000/api) 
 * and production Render deployment (https://datasense-ai.onrender.com/api).
 */

import axios from 'axios';

const DIRECT_BACKEND_URL = 'https://datasense-ai-59kk.onrender.com/api';

const getBaseUrl = () => {
  if (import.meta.env.VITE_API_URL) return import.meta.env.VITE_API_URL;
  if (typeof window !== 'undefined' && (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1')) {
    return '/api';
  }
  return DIRECT_BACKEND_URL;
};

const BASE_URL = getBaseUrl();

const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 300000, // 5 minutes timeout
});

export const formatApiError = (err) => {
  if (!err) return 'An unknown error occurred.';
  if (err.response) {
    const detail = err.response.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) return detail.map(d => d.msg || JSON.stringify(d)).join(' | ');
    if (err.response.status === 413) return 'File is too large. Please upload a file under 100MB.';
    if (err.response.status === 500) return 'Backend server error during processing. Please verify file format and try again.';
    if (err.response.status === 504) return 'Server request timed out. Render server may be starting up.';
    return `Server returned error (${err.response.status}): ${err.response.statusText || 'Operation failed'}`;
  }
  if (err.code === 'ECONNABORTED' || err.message?.includes('timeout')) {
    return 'Upload timed out. The Render backend instance may be spinning up from idle state. Please try again.';
  }
  if (err.message === 'Network Error' || !err.status) {
    return 'Cannot connect to backend server. Render free instance may take ~30s to wake up from idle. Please wait a moment and try again.';
  }
  return err.message || 'Operation failed. Please check network connection.';
};

export const uploadDataset = async (file, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);

  const uploadUrl = BASE_URL.endsWith('/') 
    ? `${BASE_URL}datasets/upload` 
    : `${BASE_URL}/datasets/upload`;

  try {
    const response = await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
      timeout: 600000, // 10 minutes timeout for 300,000 row files
    });
    return response.data;
  } catch (err) {
    throw new Error(formatApiError(err));
  }
};

export const getDatasetProfile = async (datasetId) => {
  try {
    const response = await apiClient.get(`/datasets/${datasetId}/profile`);
    return response.data;
  } catch (err) {
    throw new Error(formatApiError(err));
  }
};

export const askQuestion = async (datasetId, question, mode = 'auto') => {
  try {
    const response = await apiClient.post('/ask', {
      dataset_id: datasetId,
      question: question,
      mode: mode,
    });
    return response.data;
  } catch (err) {
    throw new Error(formatApiError(err));
  }
};

export const uploadContextFile = async (file, onProgress = null) => {
  const formData = new FormData();
  formData.append('file', file);

  const uploadUrl = BASE_URL.endsWith('/') 
    ? `${BASE_URL}context/upload` 
    : `${BASE_URL}/context/upload`;

  try {
    const response = await axios.post(uploadUrl, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      onUploadProgress: (progressEvent) => {
        if (onProgress && progressEvent.total) {
          const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          onProgress(percentCompleted);
        }
      },
      timeout: 600000,
    });
    return response.data;
  } catch (err) {
    throw new Error(formatApiError(err));
  }
};

export const getContextDocuments = async () => {
  try {
    const response = await apiClient.get('/context/documents');
    return response.data;
  } catch (err) {
    throw new Error(formatApiError(err));
  }
};

export default apiClient;
