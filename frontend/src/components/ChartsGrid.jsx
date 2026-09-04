import React from 'react';
import Plotly from 'plotly.js-dist-min';
import createPlotlyComponent from 'react-plotly.js/factory';
import { BarChart3 } from 'lucide-react';

const Plot = createPlotlyComponent(Plotly);

export default function ChartsGrid({ profileData, loading }) {
  if (loading) {
    return (
      <div className="charts-loading">
        <div className="spinner"></div>
        <p>Auto-profiling dataset and building Plotly visualizations...</p>
      </div>
    );
  }

  if (!profileData || !profileData.charts || profileData.charts.length === 0) {
    return (
      <div className="charts-empty">
        <BarChart3 className="icon-large text-gray" />
        <p>No automated profile charts available for this dataset.</p>
      </div>
    );
  }

  return (
    <div className="charts-section">
      <h3 className="section-title">
        <BarChart3 className="icon-small text-blue" /> Auto-Profiled Visual Insights
      </h3>
      <div className="charts-grid">
        {profileData.charts.map((chart) => (
          <div key={chart.chart_id} className="chart-card">
            <h4 className="chart-title">{chart.title}</h4>
            <div className="plotly-container">
              <Plot
                data={chart.plotly_spec.data}
                layout={{
                  ...chart.plotly_spec.layout,
                  autosize: true,
                  responsive: true,
                }}
                useResizeHandler={true}
                style={{ width: '100%', height: '320px' }}
                config={{ responsive: true, displayModeBar: false }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
