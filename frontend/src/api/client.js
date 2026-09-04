/**
 * API Client Service
 * Handles HTTP requests to the FastAPI DataSense backend endpoints.
 * Automatically adapts between local development (http://localhost:8000/api) 
 * and production Vercel/Render deployments.
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

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const uploadUrl = BASE_URL.endsWith('/') 
    ? `${BASE_URL}datasets/upload` 
    : `${BASE_URL}/datasets/upload`;

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

  const uploadUrl = BASE_URL.endsWith('/') 
    ? `${BASE_URL}context/upload` 
    : `${BASE_URL}/context/upload`;

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
