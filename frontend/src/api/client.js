/**
 * API Client Service
 * Handles HTTP requests to the FastAPI DataSense backend endpoints.
 * Automatically adapts between local development (http://localhost:8000/api) 
 * and production Vercel/Render deployments.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

// For large file uploads, bypass Vercel's 4.5MB proxy limit in production by connecting directly to Render
const DIRECT_BACKEND_URL = 'https://datasense-ai-59kk.onrender.com/api';
const UPLOAD_BASE_URL = import.meta.env.VITE_API_URL || 
  (typeof window !== 'undefined' && window.location.hostname === 'localhost' ? '/api' : DIRECT_BACKEND_URL);

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 120000, // 2 minutes
});

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const uploadUrl = UPLOAD_BASE_URL.endsWith('/') 
    ? `${UPLOAD_BASE_URL}datasets/upload` 
    : `${UPLOAD_BASE_URL}/datasets/upload`;

  const response = await axios.post(uploadUrl, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 600000, // 10 minutes timeout for 300,000 row files
  });
  return response.data;
};

export const getDatasetProfile = async (datasetId) => {
  const response = await apiClient.get(`/datasets/${datasetId}/profile`);
  return response.data;
};

export const askQuestion = async (datasetId, question, mode = 'auto') => {
  const response = await apiClient.post('/ask', {
    dataset_id: datasetId,
    question: question,
    mode: mode,
  });
  return response.data;
};

export const uploadContextFile = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const uploadUrl = UPLOAD_BASE_URL.endsWith('/') 
    ? `${UPLOAD_BASE_URL}context/upload` 
    : `${UPLOAD_BASE_URL}/context/upload`;

  const response = await axios.post(uploadUrl, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    timeout: 600000,
  });
  return response.data;
};

export const getContextDocuments = async () => {
  const response = await apiClient.get('/context/documents');
  return response.data;
};

export default apiClient;
