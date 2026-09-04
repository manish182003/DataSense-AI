import React from 'react';
import { Database, Columns, AlertTriangle, Hash } from 'lucide-react';

export default function KpiCards({ metadata }) {
  if (!metadata) return null;

  const { row_count, column_count, total_missing_percentage, columns } = metadata;
  
  const numericCount = columns.filter(c => 
    ['int', 'float', 'double', 'int64', 'float64', 'numeric'].some(t => c.dtype.toLowerCase().includes(t))
  ).length;

  const categoricalCount = column_count - numericCount;

  return (
    <div className="kpi-grid">
      <div className="kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Total Rows</span>
          <Database className="kpi-icon text-blue" />
        </div>
        <div className="kpi-value">{row_count.toLocaleString()}</div>
        <div className="kpi-footer">Records in DuckDB</div>
      </div>

      <div className="kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Total Columns</span>
          <Columns className="kpi-icon text-emerald" />
        </div>
        <div className="kpi-value">{column_count}</div>
        <div className="kpi-footer">{numericCount} Numeric • {categoricalCount} Categorical</div>
      </div>

      <div className="kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">Missing Values</span>
          <AlertTriangle className="kpi-icon text-amber" />
        </div>
        <div className="kpi-value">{total_missing_percentage}%</div>
        <div className="kpi-footer">Across all data cells</div>
      </div>

      <div className="kpi-card">
        <div className="kpi-header">
          <span className="kpi-title">DuckDB Table</span>
          <Hash className="kpi-icon text-purple" />
        </div>
        <div className="kpi-value table-name">{metadata.dataset_id}</div>
        <div className="kpi-footer">{metadata.filename}</div>
      </div>
    </div>
  );
}
