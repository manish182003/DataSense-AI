import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Code, ChevronDown, ChevronUp, Copy, Check, Table, Sparkles, Loader2, BookOpen, Cpu, BarChart3, FileText } from 'lucide-react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import MarkdownRenderer from './MarkdownRenderer';
import { askQuestion } from '../api/client';

const Plot = createPlotlyComponent(Plotly);

/**
 * Intelligent helper to decide if a query genuinely warrants a visual Chart.
 */
function shouldDisplayChart(question, results, routeUsed) {
  if (routeUsed === 'rag') return false;
  if (!results || !Array.isArray(results) || results.length < 2) return false;

  const qLower = (question || '').toLowerCase();
  
  // Explicit chart request keywords (graph, chart, plot, visualize, against, vs, per, etc.)
  const isExplicitChart = /\b(graph|chart|plot|draw|visual|visualize|visualization|against|vs|versus|per|deafult|default|decile|rate)\b/i.test(qLower);
  if (isExplicitChart) return true;

  // Comparative/trend/grouping keywords
  const hasComparativeIntent = /\b(top|highest|lowest|by|breakdown|trend|monthly|yearly|compare|distribution|rank|categories|regions|sales|revenue|units|group)\b/i.test(qLower);
  if (hasComparativeIntent) return true;

  // Show chart for any result with 2+ rows and 2+ columns
  if (results.length >= 2) {
    const keys = Object.keys(results[0]);
    if (keys.length >= 2) return true;
  }

  return false;
}

/**
 * Intelligent helper to decide if raw SQL Data Table should be displayed below explanation.
 */
function shouldDisplayDataTable(results, routeUsed, explanationText) {
  if (routeUsed === 'rag') return false;
  if (!results || !Array.isArray(results) || results.length === 0) return false;

  // Single scalar result (e.g. count or total sum) is already answered in Executive Insights text
  if (results.length === 1 && Object.keys(results[0]).length <= 2) return false;

  // If explanation text already contains a parsed Markdown Table, do not duplicate raw table
  const explanationHasTable = explanationText && explanationText.includes('|') && explanationText.includes('---');
  if (explanationHasTable) return false;

  return true;
}

/**
 * Extracts Plotly chart trace and layout specs from query result rows.
 */
function buildQueryChartSpec(results) {
  if (!results || !Array.isArray(results) || results.length < 2) return null;
  
  const keys = Object.keys(results[0]);
  if (keys.length < 2) return null;

  // Classify columns into numeric vs categorical/date
  const numericKeys = [];
  const categoricalKeys = [];

  keys.forEach(key => {
    let numMatches = 0;
    let validCount = 0;

    results.forEach(row => {
      const val = row[key];
      if (val !== null && val !== undefined && val !== '') {
        validCount++;
        const numVal = Number(val);
        if (!isNaN(numVal) && typeof val !== 'boolean') {
          numMatches++;
        }
      }
    });

    if (validCount > 0 && (numMatches / validCount) >= 0.6) {
      numericKeys.push(key);
    } else {
      categoricalKeys.push(key);
    }
  });

  let xKey = categoricalKeys[0] || keys[0];
  let yKey = numericKeys.find(k => k !== xKey) || keys[1];

  if (!xKey || !yKey || xKey === yKey) {
    xKey = keys[0];
    yKey = keys[1];
  }

  const rawXVals = results.map(r => (r[xKey] === null || r[xKey] === undefined) ? 'N/A' : String(r[xKey]));
  const yVals = results.map(r => {
    const v = Number(r[yKey]);
    return isNaN(v) ? 0 : v;
  });

  const truncatedXVals = rawXVals.map(x => x.length > 22 ? x.substring(0, 19) + '...' : x);

  const isDateSeq = rawXVals.every(x => 
    /^\d{4}(-\d{2})?(-\d{2})?$/.test(x) || 
    /^\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4}$/.test(x) || 
    /^(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)/i.test(x)
  );

  const chartType = isDateSeq ? 'Line Trend' : 'Bar Chart';

  const dataTrace = isDateSeq ? {
    x: rawXVals,
    y: yVals,
    type: 'scatter',
    mode: 'lines+markers',
    text: rawXVals,
    line: { color: '#38bdf8', width: 3, shape: 'spline' },
    marker: { color: '#60a5fa', size: 8 },
    hovertemplate: '<b>%{text}</b><br>' + yKey + ': <b>%{y:,.2f}</b><extra></extra>'
  } : {
    x: truncatedXVals,
    y: yVals,
    type: 'bar',
    text: rawXVals,
    marker: {
      color: yVals.map((_, i) => `hsl(${205 + (i * 15) % 65}, 85%, 60%)`),
      line: { color: '#3b82f6', width: 1 },
      corner_radius: 6
    },
    hovertemplate: '<b>%{text}</b><br>' + yKey + ': <b>%{y:,.2f}</b><extra></extra>'
  };

  const layout = {
    paper_bgcolor: '#151c2c',
    plot_bgcolor: '#0b0f19',
    font: { color: '#f8fafc', family: 'Inter, system-ui, sans-serif', size: 12 },
    xaxis: { 
      gridcolor: '#232d42', 
      title: { text: xKey, font: { color: '#94a3b8', size: 12 } },
      tickangle: truncatedXVals.some(x => x.length > 8) ? -25 : 0,
      automargin: true
    },
    yaxis: { 
      gridcolor: '#232d42', 
      title: { text: yKey, font: { color: '#94a3b8', size: 12 } },
      zerolinecolor: '#334155',
      automargin: true
    },
    margin: { l: 60, r: 30, t: 30, b: 60 },
    height: 300,
    autosize: true
  };

  return {
    trace: dataTrace,
    layout: layout,
    xKey: xKey,
    yKey: yKey,
    chartType: chartType
  };
}

export default function AskChat({ datasetId, columns }) {
  const [question, setQuestion] = useState('');
  const [mode, setMode] = useState('auto');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [response, setResponse] = useState(null);
  const [showSql, setShowSql] = useState(false);
  const [copied, setCopied] = useState(false);
  const responseRef = useRef(null);

  const sampleQuestions = [
    { text: "What are the top sales sub-categories by total revenue?", mode: "nl2sql" },
    { text: "Show total sales and profit by region", mode: "nl2sql" },
    { text: "What is our company return policy window?", mode: "rag" },
  ];

  useEffect(() => {
    if (response && responseRef.current) {
      responseRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [response]);

  const handleAsk = async (queryText, forceMode) => {
    const activeQuery = queryText || question;
    const activeMode = forceMode || mode;
    if (!activeQuery.trim() || !datasetId) return;

    setLoading(true);
    setError(null);

    try {
      const res = await askQuestion(datasetId, activeQuery, activeMode);
      setResponse(res);
      setShowSql(false);
    } catch (err) {
      console.error('Ask Error:', err);
      setError(err.response?.data?.detail || 'Unable to process query. Please check dataset status or Groq configuration.');
    } finally {
      setLoading(false);
    }
  };

  const handleCopySql = () => {
    if (response?.sql) {
      navigator.clipboard.writeText(response.sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  // Determine visibility of Chart and Table
  const canShowChart = response ? shouldDisplayChart(response.question, response.results, response.route_used) : false;
  const chartSpec = canShowChart ? buildQueryChartSpec(response.results) : null;
  const canShowDataTable = response ? shouldDisplayDataTable(response.results, response.route_used, response.explanation) : false;

  return (
    <div className="ask-container">
      <div className="ask-header">
        <div className="header-top-bar">
          <div className="header-title-group">
            <h3 className="section-title">
              <Sparkles className="icon-small text-amber" /> DataSense Assistant
            </h3>
            <p className="section-subtitle">
              Natural Language Data Analytics & Business Knowledge Query Engine
            </p>
          </div>

          <div className="engine-select-wrapper">
            <span className="engine-label">Engine:</span>
            <select 
              value={mode} 
              onChange={(e) => setMode(e.target.value)}
              className="engine-dropdown"
              disabled={loading}
            >
              <option value="auto">✨ Auto (Smart Assistant)</option>
              <option value="nl2sql">📊 Data Analytics Engine</option>
              <option value="rag">📚 Business Knowledge Base</option>
            </select>
          </div>
        </div>
      </div>

      {/* Suggested Questions */}
      <div className="suggestions-row">
        <span className="suggestions-label">Try asking:</span>
        {sampleQuestions.map((q, idx) => (
          <button
            key={idx}
            className="suggestion-chip"
            onClick={() => {
              setQuestion(q.text);
              setMode(q.mode);
              handleAsk(q.text, q.mode);
            }}
            disabled={loading}
          >
            {q.text}
          </button>
        ))}
      </div>

      {/* Query Input Bar */}
      <form onSubmit={(e) => { e.preventDefault(); handleAsk(); }} className="ask-input-form">
        <div className="input-wrapper">
          <MessageSquare className="input-icon text-gray" />
          <input
            type="text"
            className="ask-input"
            placeholder="Ask a question about your uploaded dataset or business policy..."
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            disabled={loading}
          />
          <button type="submit" className="send-btn" disabled={loading || !question.trim()}>
            {loading ? <Loader2 className="animate-spin icon-small" /> : <Send className="icon-small" />}
            <span>{loading ? 'Analyzing...' : 'Ask'}</span>
          </button>
        </div>
      </form>

      {error && (
        <div className="error-banner margin-top">
          <span>{error}</span>
        </div>
      )}

      {/* Response Panel */}
      {response && (
        <div className="response-panel" ref={responseRef}>
          
          {/* Answer Source Badge */}
          <div className="route-badge-row">
            {response.route_used === 'rag' ? (
              <span className="badge badge-rag">
                <BookOpen className="icon-tiny" /> Answer Source: Business Policy & Knowledge Base
              </span>
            ) : (
              <span className="badge badge-nl2sql">
                <Cpu className="icon-tiny" /> Answer Source: Tabular Data Analytics Engine
              </span>
            )}
          </div>

          {/* Plain Language Executive Summary */}
          <div className="explanation-box">
            <div className="box-title">
              <Sparkles className="icon-small text-blue" /> Executive Insights
            </div>
            <div className="explanation-content">
              <MarkdownRenderer content={response.explanation} />
            </div>

            {/* Citations for Knowledge Base queries */}
            {response.retrieved_chunks && response.retrieved_chunks.length > 0 && (
              <div className="citation-bar">
                <span className="citation-label">
                  <FileText className="icon-tiny text-purple" /> Source Documents:
                </span>
                {Array.from(new Set(response.retrieved_chunks.map(c => `${c.source_doc} (p. ${c.page_number})`))).map((sourceStr, sIdx) => (
                  <span key={sIdx} className="citation-badge-chip">
                    [Doc: {sourceStr}]
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Query Result Chart (Rendered ONLY when comparative/trend visualization is genuinely needed) */}
          {chartSpec && (
            <div className="query-chart-card margin-top">
              <div className="query-chart-header">
                <div className="chart-header-left">
                  <BarChart3 className="icon-small text-emerald" />
                  <span className="query-chart-title">Data Analytics Visualization</span>
                  <span className="chart-type-pill">{chartSpec.chartType}</span>
                </div>
                <span className="chart-subtitle-text">
                  Showing <strong>{chartSpec.yKey}</strong> by <strong>{chartSpec.xKey}</strong>
                </span>
              </div>

              <div className="plotly-container">
                <Plot
                  data={[chartSpec.trace]}
                  layout={chartSpec.layout}
                  useResizeHandler={true}
                  style={{ width: '100%', height: '300px' }}
                  config={{ responsive: true, displayModeBar: false }}
                />
              </div>
            </div>
          )}

          {/* Raw SQL Data Table (Rendered ONLY when table is NOT already parsed in explanation & results > 1) */}
          {canShowDataTable && (
            <div className="results-table-container margin-top">
              <div className="table-header-bar">
                <Table className="icon-small text-purple" />
                <span>Query Result Data ({response.row_count} rows)</span>
              </div>
              <div className="table-scroll-wrapper">
                <table className="results-table">
                  <thead>
                    <tr>
                      {Object.keys(response.results[0]).map((key) => (
                        <th key={key}>{key}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {response.results.map((row, rIdx) => (
                      <tr key={rIdx}>
                        {Object.values(row).map((val, cIdx) => (
                          <td key={cIdx}>
                            {val === null || val === undefined ? <span className="null-val">null</span> : String(val)}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Collapsible DuckDB SQL Block (Shown ONLY for SQL queries, default collapsed) */}
          {response.route_used !== 'rag' && response.sql && (
            <div className="sql-box margin-top">
              <div className="sql-header" onClick={() => setShowSql(!showSql)}>
                <div className="sql-title">
                  <Code className="icon-small text-emerald" /> Underlying DuckDB SQL Statement
                </div>
                <div className="sql-actions">
                  <button 
                    className="copy-btn" 
                    onClick={(e) => { e.stopPropagation(); handleCopySql(); }}
                    title="Copy SQL query"
                  >
                    {copied ? <Check className="icon-tiny text-emerald" /> : <Copy className="icon-tiny" />}
                    <span>{copied ? 'Copied!' : 'Copy SQL'}</span>
                  </button>
                  {showSql ? <ChevronUp className="icon-small" /> : <ChevronDown className="icon-small" />}
                </div>
              </div>

              {showSql && (
                <pre className="sql-code-block">
                  <code>{response.sql}</code>
                </pre>
              )}
            </div>
          )}

        </div>
      )}
    </div>
  );
}
