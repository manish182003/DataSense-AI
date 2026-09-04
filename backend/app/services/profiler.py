"""
Profiler Service
Computes summary statistics for dataset columns and generates Plotly chart specifications
(Histograms, Top-N Bar Charts, Correlation Heatmaps, and Time Trends).
"""

import math
import pandas as pd
import numpy as np
from typing import Dict, Any, List, Optional
from app.schemas.payload import ProfileResponse, ProfileChart

# Modern Dark Theme Palette for Plotly Charts
CHART_LAYOUT_THEME = {
    "paper_bgcolor": "#1e293b",
    "plot_bgcolor": "#0f172a",
    "font": {"color": "#f8fafc", "family": "Inter, sans-serif"},
    "xaxis": {"gridcolor": "#334155", "zerolinecolor": "#475569"},
    "yaxis": {"gridcolor": "#334155", "zerolinecolor": "#475569"},
    "margin": {"l": 50, "r": 30, "t": 50, "b": 50}
}

def safe_float(val: Any) -> float:
    """
    Converts numpy/pandas numbers to standard JSON-serializable float, replacing NaN/Inf with 0.0.
    """
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return 0.0
        return round(f, 4)
    except Exception:
        return 0.0

def generate_column_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Computes summary statistics for each column in a JSON-safe manner.
    Safely samples up to 5,000 rows for high performance.
    """
    sample_df = df.sample(min(5000, len(df)), random_state=42) if len(df) > 5000 else df
    stats = {}
    for col in sample_df.columns:
        col_data = sample_df[col].dropna()
        if pd.api.types.is_numeric_dtype(sample_df[col]):
            stats[col] = {
                "type": "numeric",
                "count": int(len(col_data)),
                "mean": safe_float(col_data.mean()) if len(col_data) > 0 else 0.0,
                "std": safe_float(col_data.std()) if len(col_data) > 1 else 0.0,
                "min": safe_float(col_data.min()) if len(col_data) > 0 else 0.0,
                "max": safe_float(col_data.max()) if len(col_data) > 0 else 0.0,
                "median": safe_float(col_data.median()) if len(col_data) > 0 else 0.0,
            }
        else:
            mode_res = col_data.mode()
            top_val = str(mode_res.iloc[0]) if not mode_res.empty else None
            stats[col] = {
                "type": "categorical",
                "count": int(len(col_data)),
                "unique": int(col_data.nunique()),
                "top_value": top_val,
            }
    return stats

def generate_profile_charts(df: pd.DataFrame) -> List[ProfileChart]:
    """
    Auto-selects and generates 4-6 Plotly figure specs based on dataset column types.
    """
    charts: List[ProfileChart] = []

    # Detect numeric columns
    numeric_cols = [col for col in df.columns if pd.api.types.is_numeric_dtype(df[col])]
    
    # Detect datetime columns (explicit datetime or object columns parsing cleanly to dates)
    datetime_cols = []
    parsed_dates = {}
    
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            datetime_cols.append(col)
            parsed_dates[col] = df[col]
        elif not pd.api.types.is_numeric_dtype(df[col]):
            # Try parsing string dates
            try:
                sample_s = df[col].dropna().astype(str).head(30)
                if any(c in col.lower() for c in ['date', 'time', 'year', 'day']) or sample_s.str.contains(r'\d{1,4}[-/]\d{1,2}[-/]\d{1,4}').any():
                    converted = pd.to_datetime(df[col], errors='coerce')
                    if converted.notnull().sum() > 0.5 * len(df[col].dropna()):
                        datetime_cols.append(col)
                        parsed_dates[col] = converted
            except Exception:
                pass

    categorical_cols = [col for col in df.columns if col not in numeric_cols and col not in datetime_cols]

    # 1. Numeric Distribution Charts (up to 2 histograms)
    for col in numeric_cols[:2]:
        vals = [safe_float(v) for v in df[col].dropna().head(2000)]
        if len(vals) > 0:
            fig_spec = {
                "data": [{
                    "x": vals,
                    "type": "histogram",
                    "marker": {"color": "#3b82f6", "line": {"color": "#1d4ed8", "width": 1}},
                    "opacity": 0.85
                }],
                "layout": {
                    **CHART_LAYOUT_THEME,
                    "title": f"Distribution of {col}",
                    "xaxis": {**CHART_LAYOUT_THEME["xaxis"], "title": col},
                    "yaxis": {**CHART_LAYOUT_THEME["yaxis"], "title": "Frequency"}
                }
            }
            charts.append(ProfileChart(
                chart_id=f"hist_{col}",
                title=f"Distribution of {col}",
                chart_type="histogram",
                plotly_spec=fig_spec
            ))

    # 2. Categorical Top-N Bar Charts (up to 2 bar charts)
    for col in categorical_cols[:2]:
        top_counts = df[col].value_counts().head(10)
        if not top_counts.empty:
            fig_spec = {
                "data": [{
                    "x": top_counts.index.astype(str).tolist(),
                    "y": [int(v) for v in top_counts.values],
                    "type": "bar",
                    "marker": {"color": "#10b981", "line": {"color": "#047857", "width": 1}}
                }],
                "layout": {
                    **CHART_LAYOUT_THEME,
                    "title": f"Top Values in {col}",
                    "xaxis": {**CHART_LAYOUT_THEME["xaxis"], "title": col},
                    "yaxis": {**CHART_LAYOUT_THEME["yaxis"], "title": "Count"}
                }
            }
            charts.append(ProfileChart(
                chart_id=f"bar_{col}",
                title=f"Top Values in {col}",
                chart_type="bar",
                plotly_spec=fig_spec
            ))

    # 3. Time Trend Line Chart (if date/datetime column exists)
    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        val_col = numeric_cols[0]
        date_series = parsed_dates[date_col]
        
        temp_df = pd.DataFrame({"dt": date_series, "val": df[val_col]}).dropna().sort_values(by="dt")
        # Aggregate by date/month if large dataset
        if len(temp_df) > 50:
            temp_df["dt_group"] = temp_df["dt"].dt.to_period("M").dt.to_timestamp()
            temp_df = temp_df.groupby("dt_group")["val"].mean().reset_index().rename(columns={"dt_group": "dt"})
        
        temp_df = temp_df.head(200)
        if len(temp_df) > 1:
            fig_spec = {
                "data": [{
                    "x": temp_df["dt"].dt.strftime('%Y-%m-%d').tolist(),
                    "y": [safe_float(v) for v in temp_df["val"]],
                    "type": "scatter",
                    "mode": "lines+markers",
                    "line": {"color": "#8b5cf6", "width": 2},
                    "marker": {"size": 6}
                }],
                "layout": {
                    **CHART_LAYOUT_THEME,
                    "title": f"Time Trend: {val_col} over {date_col}",
                    "xaxis": {**CHART_LAYOUT_THEME["xaxis"], "title": date_col},
                    "yaxis": {**CHART_LAYOUT_THEME["yaxis"], "title": val_col}
                }
            }
            charts.append(ProfileChart(
                chart_id=f"trend_{date_col}_{val_col}",
                title=f"{val_col} over {date_col}",
                chart_type="line",
                plotly_spec=fig_spec
            ))

    # 4. Correlation Heatmap (if >= 2 numeric columns exist)
    if len(numeric_cols) >= 2:
        num_df = df[numeric_cols[:6]].dropna()
        if len(num_df) > 1:
            corr_matrix = num_df.corr().fillna(0.0).round(2)
            z_vals = [[safe_float(cell) for cell in row] for row in corr_matrix.values]
            fig_spec = {
                "data": [{
                    "z": z_vals,
                    "x": corr_matrix.columns.tolist(),
                    "y": corr_matrix.index.tolist(),
                    "type": "heatmap",
                    "colorscale": "Viridis",
                    "showscale": True
                }],
                "layout": {
                    **CHART_LAYOUT_THEME,
                    "title": "Numeric Correlation Heatmap"
                }
            }
            charts.append(ProfileChart(
                chart_id="correlation_heatmap",
                title="Correlation Heatmap",
                chart_type="heatmap",
                plotly_spec=fig_spec
            ))

    return charts

def build_dataset_profile(dataset_id: str, df: pd.DataFrame) -> ProfileResponse:
    """
    Generates summary statistics and auto-profiled Plotly visual specs.
    Safely limits input dataframe to max 5,000 rows for high performance and low RAM footprint.
    """
    sample_df = df.head(5000) if len(df) > 5000 else df
    stats = generate_column_stats(sample_df)
    charts = generate_profile_charts(sample_df)
    return ProfileResponse(
        dataset_id=dataset_id,
        summary_stats=stats,
        charts=charts
    )
