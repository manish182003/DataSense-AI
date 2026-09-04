import React, { useState } from 'react';
import { Database, UploadCloud, RefreshCw, BarChart2, Zap, BookOpen, LayoutDashboard, ShieldCheck } from 'lucide-react';
import DatasetUpload from './components/DatasetUpload';
import KpiCards from './components/KpiCards';
import ChartsGrid from './components/ChartsGrid';
import AskChat from './components/AskChat';
import KnowledgeBaseView from './components/KnowledgeBaseView';
import EvalDashboard from './components/EvalDashboard';
import { getDatasetProfile } from './api/client';
import './index.css';

export default function App() {
  const [metadata, setMetadata] = useState(null);
  const [profileData, setProfileData] = useState(null);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [activeTab, setActiveTab] = useState('dashboard');

  const handleUploadSuccess = async (newMetadata) => {
    setMetadata(newMetadata);
    setLoadingProfile(true);

    try {
      const profile = await getDatasetProfile(newMetadata.dataset_id);
      setProfileData(profile);
    } catch (err) {
      console.error('Failed to fetch profile:', err);
    } finally {
      setLoadingProfile(false);
    }
  };

  const handleReset = () => {
    setMetadata(null);
    setProfileData(null);
  };

  return (
    <div className="app-container">
      {/* Top Navbar */}
      <header className="navbar">
        <div className="navbar-brand">
          <div className="brand-icon">
            <Zap className="icon-medium text-blue" />
          </div>
          <div>
            <h1 className="brand-title">DataSense</h1>
            <span className="brand-subtitle">Production Data-to-Insight Platform</span>
          </div>
        </div>

        {/* Tab Navigation */}
        <div className="nav-tabs">
          <button 
            className={`nav-tab ${activeTab === 'dashboard' ? 'active' : ''}`}
            onClick={() => setActiveTab('dashboard')}
          >
            <LayoutDashboard className="icon-small" /> Data Analytics
          </button>
          <button 
            className={`nav-tab ${activeTab === 'knowledge' ? 'active' : ''}`}
            onClick={() => setActiveTab('knowledge')}
          >
            <BookOpen className="icon-small text-purple" /> Business Knowledge Base
          </button>
        </div>

        <div className="navbar-actions">
          {metadata && activeTab === 'dashboard' && (
            <>
              <div className="active-dataset-badge">
                <Database className="icon-tiny text-emerald" />
                <span>{metadata.filename}</span>
              </div>
              <button className="btn-secondary" onClick={handleReset}>
                <UploadCloud className="icon-small" /> Upload New Dataset
              </button>
            </>
          )}
        </div>
      </header>

      {/* Main Content Body */}
      <main className="main-content">
        {activeTab === 'eval' ? (
          <EvalDashboard />
        ) : activeTab === 'knowledge' ? (
          <KnowledgeBaseView />
        ) : (
          !metadata ? (
            <div className="hero-section">
              <div className="hero-header">
                <h2 className="hero-title">Transform Tabular Data into Instant Intelligence</h2>
                <p className="hero-description">
                  Upload CSV, Excel, or JSON files. Automated profiling generates Plotly charts instantly, 
                  and Groq LLM converts natural language questions directly into executable DuckDB SQL queries.
                </p>
              </div>
              <DatasetUpload onUploadSuccess={handleUploadSuccess} />
            </div>
          ) : (
            <div className="dashboard-layout">
              {/* KPI Overview Cards */}
              <KpiCards metadata={metadata} />

              {/* Auto-Profiled Visual Charts Grid */}
              <ChartsGrid profileData={profileData} loading={loadingProfile} />

              {/* NL2SQL & RAG Ask Assistant */}
              <AskChat datasetId={metadata.dataset_id} columns={metadata.columns} />
            </div>
          )
        )}
      </main>
    </div>
  );
}
