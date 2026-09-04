/**
 * API Client Service
 * Handles HTTP requests to the FastAPI DataSense backend endpoints.
 * Automatically adapts between local development (http://localhost:8000/api) 
 * and production Vercel/Render deployments.
 */

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const uploadDataset = async (file) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await axios.post(`${API_BASE_URL}/datasets/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
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

  const response = await axios.post(`${API_BASE_URL}/context/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  });
  return response.data;
};

export const getContextDocuments = async () => {
  const response = await apiClient.get('/context/documents');
  return response.data;
};

export default apiClient;
