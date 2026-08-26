import pandas as pd
import numpy as np
import os
import base64
import io
import tempfile
from pathlib import Path
import plotly.graph_objects as go
import dash
from dash import html, dcc, Input, Output, State, dash_table, ALL
import dash_bootstrap_components as dbc
from app import app
from datetime import datetime
from apps.dwm_parser import parse_dwm_excel, upsert_dwm_data, convert_excel_to_csvs_bg

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
MONTHLY_CSV = DATA_DIR / "dwm_monthly.csv"
DAILY_CSV = DATA_DIR / "dwm_daily.csv"

def load_dwm_monthly():
    if MONTHLY_CSV.exists():
        try:
            df = pd.read_csv(MONTHLY_CSV)
            if 'section' not in df.columns:
                df['section'] = ""
            if 'sub_section' not in df.columns:
                df['sub_section'] = ""
            df['date'] = pd.to_datetime(df['date'])
            df['value'] = pd.to_numeric(df['value'], errors='coerce')
            df = df.sort_values('date')
            return df
        except Exception as e:
            print(f"Error loading DWM monthly CSV: {e}")
    return pd.DataFrame(columns=["source_file", "department", "section", "sub_section", "kpi_name", "uom", "type", "date", "value"])

def load_dwm_daily():
    if DAILY_CSV.exists():
        try:
            df = pd.read_csv(DAILY_CSV)
            df['date'] = pd.to_datetime(df['date'])
            for col in ['actual', 'plan', 'ucl', 'cl', 'lcl']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.sort_values('date')
            return df
        except Exception as e:
            print(f"Error loading DWM daily CSV: {e}")
    return pd.DataFrame(columns=["source_file", "department", "section", "sub_section", "kpi_name", "sheet_name", "month_year", "date", "actual", "plan", "ucl", "cl", "lcl"])

# --- DYNAMIC LAYOUT FUNCTION ---
def layout():
    df_m = load_dwm_monthly()
    df_d = load_dwm_daily()
    
    # Get all unique departments from consolidated CSVs
    depts_m = df_m['department'].dropna().unique().tolist()
    depts_d = df_d['department'].dropna().unique().tolist()
    all_depts = sorted(list(set(depts_m + depts_d)))
    
    default_dept = all_depts[0] if all_depts else None

    return dbc.Container([
        dcc.Store(id="dwm-uploaded-data-store", storage_type="session"),
        dcc.Store(id="dwm-modal-data-store", storage_type="session"),
        dcc.Store(id="dwm-custom-chart-store", storage_type="session"),
        
        dbc.Row([
            dbc.Col([
                html.Div([
                    html.H2("Daily Management Dashboard", className="text-primary", style={"fontWeight": "bold", "marginBottom": "5px"}),
                    html.P("Monitor daily checking points, control limits, and monthly managing KPI trends across departments.", className="text-muted")
                ], className="py-3")
            ])
        ]),
        
        # Tabs for Departments and Upload Button
        dbc.Row([
            dbc.Col([
                dbc.Tabs(
                    id="dwm-dept-tabs",
                    active_tab=default_dept,
                    children=[
                        dbc.Tab(label=dept, tab_id=dept, tab_style={"cursor": "pointer"}) for dept in all_depts
                    ]
                )
            ], lg=9, md=8, xs=12),
            dbc.Col([
                dbc.Button(
                    "➕ Upload Department",
                    id="dwm-upload-dept-btn",
                    color="primary",
                    className="float-end",
                    style={"borderRadius": "8px", "fontWeight": "600"}
                )
            ], lg=3, md=4, xs=12)
        ], className="align-items-center mb-4"),
        
        # Delete notification alert container
        html.Div(id="dwm-delete-notification-container"),
        
        # Container for the department view (KPI dropdown and charts)
        html.Div(id="dwm-department-view-container"),
        
        # Upload Department Modal popup
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Upload New Department", className="text-primary"), close_button=True),
            dbc.ModalBody([
                html.Div([
                    html.Label("1. Enter Department Name:", style={"fontWeight": "600", "fontSize": "14px"}),
                    dcc.Input(
                        id="dwm-upload-dept-input",
                        value="",
                        type="text",
                        placeholder="e.g. Coke Ovens, Blast Furnace...",
                        className="form-control mb-3",
                        style={"fontSize": "13px"}
                    ),
                    
                    html.Label("2. Upload Excel File:", style={"fontWeight": "600", "fontSize": "14px"}),
                    dcc.Upload(
                        id="dwm-upload-file",
                        children=html.Div(id="dwm-upload-file-label", children=[
                            html.I(className="bi bi-lock-fill me-2"),
                            "Enter department first to unlock upload"
                        ]),
                        style={
                            "width": "100%",
                            "height": "100px",
                            "lineHeight": "98px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "cursor": "not-allowed",
                            "backgroundColor": "#f1f5f9",
                            "borderColor": "#cbd5e1",
                            "color": "#64748b",
                            "fontSize": "13px",
                            "pointerEvents": "none"
                        },
                        multiple=False,
                        accept=".xls,.xlsx,.xlsm"
                    ),
                    
                    # Upload status message
                    html.Div(id="dwm-instant-upload-status", className="mt-3")
                ])
            ]),
            dbc.ModalFooter([
                dbc.Button("Close", id="dwm-upload-modal-close-btn", color="secondary", style={"borderRadius": "8px"})
            ])
        ], id="dwm-upload-dept-modal", is_open=False, size="lg", style={"borderRadius": "12px"}),
        
        # Custom Chart Modal popup
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Configure Custom Chart", className="custom-modal-title"), className="custom-modal-header"),
            dbc.ModalBody([
                html.Div([
                    html.P("We analyzed the uploaded data in the background and found that the following charts can be successfully plotted.", className="text-muted mb-4"),
                    
                    html.Label("1. Choose Chart Type", className="custom-select-label"),
                    dcc.Dropdown(
                        id="dwm-modal-chart-type",
                        options=[], # populated dynamically based on analysis
                        placeholder="Select Chart Type",
                        clearable=False,
                        className="mb-4"
                    ),
                    
                    html.Label("2. Map X-Axis Column", className="custom-select-label"),
                    dcc.Dropdown(
                        id="dwm-modal-x-axis",
                        options=[], # populated dynamically with columns of uploaded data
                        placeholder="Select X-Axis",
                        clearable=False,
                        className="mb-4"
                    ),
                    
                    html.Label("3. Map Y-Axis Column", className="custom-select-label"),
                    dcc.Dropdown(
                        id="dwm-modal-y-axis",
                        options=[], # populated dynamically with columns of uploaded data
                        placeholder="Select Y-Axis",
                        clearable=False,
                        className="mb-4"
                    )
                ])
            ], className="custom-modal-body"),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="dwm-modal-cancel-btn", color="secondary", className="me-2", style={"borderRadius": "8px"}),
                dbc.Button("Generate Chart", id="dwm-modal-generate-btn", color="primary", style={"borderRadius": "8px"})
            ], className="custom-modal-footer")
        ], id="dwm-custom-chart-modal", is_open=False, size="lg", style={"borderRadius": "12px"}),
        
        # Deletion confirmation modal popup
        dbc.Modal([
            dbc.ModalHeader(dbc.ModalTitle("Request Department Deletion", className="text-danger"), close_button=True),
            dbc.ModalBody([
                html.P(id="dwm-delete-confirm-text", style={"fontWeight": "500", "fontSize": "15px"}),
                html.P("This will send a request to the Admin. Once approved, the department tab and all its associated data will be deleted.", className="text-muted", style={"fontSize": "13px"})
            ]),
            dbc.ModalFooter([
                dbc.Button("Cancel", id="dwm-delete-confirm-cancel", color="secondary", style={"borderRadius": "8px"}),
                dbc.Button("Send Deletion Request", id="dwm-delete-confirm-send", color="danger", style={"borderRadius": "8px"})
            ])
        ], id="dwm-delete-confirm-modal", is_open=False)
        
    ], fluid=True, style={"padding": "10px"})

"""
@app.callback(
    Output("dwm-sec-dropdown", "options"),
    Output("dwm-subsec-dropdown", "options"),
    Output("dwm-kpi-dropdown", "options"),
    Output("dwm-kpi-dropdown", "value"),
    Input("dwm-dept-dropdown", "value"),
    Input("dwm-sec-dropdown", "value"),
    Input("dwm-subsec-dropdown", "value"),
    State("dwm-kpi-dropdown", "value"),
    prevent_initial_call=True
)
def sync_dwm_filters(selected_dept, selected_sec, selected_subsec, current_kpi):
    if not selected_dept:
        return [], [], [], None
        
    df_m = load_dwm_monthly()
    df_d = load_dwm_daily()
    
    # Filter data by selected department
    df_d_filtered = df_d[df_d['department'] == selected_dept]
    df_m_filtered = df_m[df_m['department'] == selected_dept]
    
    # Get sections from both datasets
    sections_d = df_d_filtered['section'].dropna().unique().tolist() if 'section' in df_d_filtered.columns else []
    sections_m = df_m_filtered['section'].dropna().unique().tolist() if 'section' in df_m_filtered.columns else []
    sections = sorted(list(set(sections_d + sections_m)))
    sections_clean = [s if str(s).strip() != "" else "General / NA" for s in sections]
    sec_options = [{"label": s_clean, "value": s} for s, s_clean in zip(sections, sections_clean) if str(s).strip() != "NA"]
    
    # Filter by section
    if selected_sec is not None:
        df_d_filtered = df_d_filtered[df_d_filtered['section'] == selected_sec]
        df_m_filtered = df_m_filtered[df_m_filtered['section'] == selected_sec]
        
    # Get sub-sections from both datasets
    sub_sections_d = df_d_filtered['sub_section'].dropna().unique().tolist() if 'sub_section' in df_d_filtered.columns else []
    sub_sections_m = df_m_filtered['sub_section'].dropna().unique().tolist() if 'sub_section' in df_m_filtered.columns else []
    sub_sections = sorted(list(set(sub_sections_d + sub_sections_m)))
    sub_sections_clean = [ss if str(ss).strip() != "" else "General / NA" for ss in sub_sections]
    subsec_options = [{"label": ss_clean, "value": ss} for ss, ss_clean in zip(sub_sections, sub_sections_clean)]
    
    # Filter by sub-section
    if selected_subsec is not None:
        df_d_filtered = df_d_filtered[df_d_filtered['sub_section'] == selected_subsec]
        df_m_filtered = df_m_filtered[df_m_filtered['sub_section'] == selected_subsec]
        
    # Get unique KPIs from both filtered datasets
    kpis_d = df_d_filtered['kpi_name'].dropna().unique().tolist() if not df_d_filtered.empty else []
    kpis_m = df_m_filtered['kpi_name'].dropna().unique().tolist() if not df_m_filtered.empty else []
    all_kpis = sorted(list(set(kpis_d + kpis_m)))
    kpi_options = [{"label": k, "value": k} for k in all_kpis]
    
    # Determine the KPI value to select
    if current_kpi and current_kpi in all_kpis:
        selected_kpi = current_kpi
    else:
        selected_kpi = all_kpis[0] if all_kpis else None
        
    return sec_options, subsec_options, kpi_options, selected_kpi
"""

def safe_float_format(val, uom="", prefix=""):
    if pd.isna(val) or val == "" or str(val).strip().lower() in ["nan", "n/a"]:
        return "N/A"
    try:
        val_float = float(val)
        return f"{prefix}{val_float:,.3g} {uom}".strip()
    except (ValueError, TypeError):
        return f"{prefix}{val} {uom}".strip()

"""
@app.callback(
    Output("dwm-metrics-cards", "children"),
    Output("dwm-tab-content", "children"),
    Input("dwm-tabs", "active_tab"),
    Input("dwm-dept-dropdown", "value"),
    Input("dwm-sec-dropdown", "value"),
    Input("dwm-subsec-dropdown", "value"),
    Input("dwm-kpi-dropdown", "value")
)
def update_dwm_dashboard(active_tab, dept, sec, subsec, kpi):
    if not kpi:
        return html.Div("Please select a KPI."), html.Div("No data available.")
        
    df_m = load_dwm_monthly()
    df_d = load_dwm_daily()
    
    # 1. Filter Data
    # Daily filter
    df_d_kpi = df_d[(df_d['department'] == dept) & (df_d['kpi_name'] == kpi)]
    if sec is not None:
        df_d_kpi = df_d_kpi[df_d_kpi['section'] == sec]
    if subsec is not None:
        df_d_kpi = df_d_kpi[df_d_kpi['sub_section'] == subsec]
        
    # Monthly filter
    df_m_kpi = df_m[(df_m['department'] == dept) & (df_m['kpi_name'] == kpi)]
    if sec is not None:
        df_m_kpi = df_m_kpi[df_m_kpi['section'] == sec]
    if subsec is not None:
        df_m_kpi = df_m_kpi[df_m_kpi['sub_section'] == subsec]
    
    # 2. Get UOM
    uom = ""
    if not df_m_kpi.empty:
        uom = str(df_m_kpi.iloc[0]['uom'])
        if uom.lower() == "nan":
            uom = ""
            
    # 3. Calculate metrics for Cards
    latest_val = "N/A"
    plan_val = "N/A"
    var_val = "N/A"
    var_pct = ""
    card_color = "secondary"
    date_str = "No recent record"
    
    # Prefer daily latest record if available, otherwise monthly
    if not df_d_kpi.empty:
        latest_row = df_d_kpi.iloc[-1]
        date_str = latest_row['date'].strftime("%Y-%m-%d")
        act = latest_row['actual']
        pl = latest_row['plan']
        
        latest_val = safe_float_format(act, uom)
        plan_val = safe_float_format(pl, uom)
            
        if pd.notna(act) and pd.notna(pl):
            try:
                act_f = float(act)
                pl_f = float(pl)
                var = act_f - pl_f
                var_val = safe_float_format(var, uom, prefix="+")
                if pl_f != 0:
                    pct = (var / pl_f) * 100
                    var_pct = f" ({pct:+.1f}%)"
                
                if var >= 0:
                    card_color = "success"
                else:
                    card_color = "danger"
            except (ValueError, TypeError):
                var_val = f"{act} - {pl}"
                
    elif not df_m_kpi.empty:
        # Monthly latest record
        latest_date = df_m_kpi['date'].max()
        df_latest_m = df_m_kpi[df_m_kpi['date'] == latest_date]
        date_str = latest_date.strftime("%B %Y")
        
        act_row = df_latest_m[df_latest_m['type'] == 'Actual']
        pl_row = df_latest_m[df_latest_m['type'] == 'Plan']
        
        act = act_row.iloc[0]['value'] if not act_row.empty else np.nan
        pl = pl_row.iloc[0]['value'] if not pl_row.empty else np.nan
        
        latest_val = safe_float_format(act, uom)
        plan_val = safe_float_format(pl, uom)
            
        if pd.notna(act) and pd.notna(pl):
            try:
                act_f = float(act)
                pl_f = float(pl)
                var = act_f - pl_f
                var_val = safe_float_format(var, uom, prefix="+")
                if pl_f != 0:
                    pct = (var / pl_f) * 100
                    var_pct = f" ({pct:+.1f}%)"
                
                if var >= 0:
                    card_color = "success"
                else:
                    card_color = "danger"
            except (ValueError, TypeError):
                var_val = f"{act} - {pl}"
                
    # Build cards layout
    metrics_row = dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Recent Period", className="text-uppercase text-muted", style={"fontSize": "11px", "fontWeight": "bold"}),
                    html.H4(date_str, className="text-dark", style={"fontWeight": "700"})
                ])
            ], className="border-0 shadow-sm", style={"borderRadius": "8px"})
        ], lg=3, md=6, xs=12, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Plan Target", className="text-uppercase text-muted", style={"fontSize": "11px", "fontWeight": "bold"}),
                    html.H4(plan_val, className="text-dark", style={"fontWeight": "700"})
                ])
            ], className="border-0 shadow-sm", style={"borderRadius": "8px"})
        ], lg=3, md=6, xs=12, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Actual Performance", className="text-uppercase text-muted", style={"fontSize": "11px", "fontWeight": "bold"}),
                    html.H4(latest_val, className="text-primary", style={"fontWeight": "700"})
                ])
            ], className="border-0 shadow-sm", style={"borderRadius": "8px"})
        ], lg=3, md=6, xs=12, className="mb-3"),
        
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Variance", className="text-uppercase text-muted", style={"fontSize": "11px", "fontWeight": "bold"}),
                    html.H4(
                        f"{var_val}{var_pct}",
                        className=f"text-{card_color}",
                        style={"fontWeight": "700"}
                    )
                ])
            ], className="border-0 shadow-sm", style={"borderRadius": "8px"})
        ], lg=3, md=6, xs=12, className="mb-3")
    ])
    
    # 4. Build Tab Content
    if active_tab == "tab-daily":
        if df_d_kpi.empty:
            tab_content = dbc.Alert("No daily checking point run chart data available for this KPI/Section. Please check the Monthly Trends tab.", color="info", className="mt-3")
        else:
            # Create Daily SPC chart
            fig = go.Figure()
            
            df_plot = df_d_kpi.sort_values('date')
            dates = df_plot['date']
            
            # UCL / CL / LCL
            if 'ucl' in df_plot.columns and df_plot['ucl'].notna().any():
                fig.add_trace(go.Scatter(x=dates, y=df_plot['ucl'], name="UCL (Upper Limit)", line=dict(color="#dc3545", width=1.5, dash="dot"), mode="lines"))
            if 'cl' in df_plot.columns and df_plot['cl'].notna().any():
                fig.add_trace(go.Scatter(x=dates, y=df_plot['cl'], name="CL (Control Limit)", line=dict(color="#6c757d", width=1.5, dash="dash"), mode="lines"))
            if 'lcl' in df_plot.columns and df_plot['lcl'].notna().any():
                fig.add_trace(go.Scatter(x=dates, y=df_plot['lcl'], name="LCL (Lower Limit)", line=dict(color="#dc3545", width=1.5, dash="dot"), mode="lines"))
                
            # Plan
            if 'plan' in df_plot.columns and df_plot['plan'].notna().any():
                fig.add_trace(go.Scatter(x=dates, y=df_plot['plan'], name="Plan Target", line=dict(color="#198754", width=2, dash="dash"), mode="lines+markers"))
                
            # Actual
            if 'actual' in df_plot.columns and df_plot['actual'].notna().any():
                fig.add_trace(go.Scatter(x=dates, y=df_plot['actual'], name="Actual Value", line=dict(color="#0d6efd", width=3), marker=dict(size=8, symbol="circle"), mode="lines+markers"))
                
            fig.update_layout(
                title=dict(text=f"Daily Run Chart: {kpi}", font=dict(size=16, color="#0f172a", family="Segoe UI")),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,1)",
                margin=dict(l=40, r=40, t=50, b=40),
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", linecolor="#cbd5e1"),
                yaxis=dict(showgrid=True, gridcolor="#e2e8f0", linecolor="#cbd5e1", title=uom),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            tab_content = dbc.Card([
                dbc.CardBody([
                    dcc.Graph(figure=fig, config={"displayModeBar": False})
                ])
            ], className="border-0 shadow-sm mt-3", style={"borderRadius": "12px"})
            
    elif active_tab == "tab-monthly":
        if df_m_kpi.empty:
            tab_content = dbc.Alert("No monthly managing KPI data available for this KPI. Please check the Daily Run Chart tab.", color="info", className="mt-3")
        else:
            # Create Monthly Actual vs Plan
            df_plot = df_m_kpi.pivot_table(index='date', columns='type', values='value').reset_index()
            df_plot = df_plot.sort_values('date')
            
            fig = go.Figure()
            dates = df_plot['date']
            
            if 'Plan' in df_plot.columns:
                fig.add_trace(go.Bar(x=dates, y=df_plot['Plan'], name="Plan Target", marker_color="#a7f3d0", opacity=0.85))
            if 'Actual' in df_plot.columns:
                fig.add_trace(go.Scatter(x=dates, y=df_plot['Actual'], name="Actual Value", line=dict(color="#0d6efd", width=3), marker=dict(size=7), mode="lines+markers"))
                
            fig.update_layout(
                title=dict(text=f"Monthly Trend: {kpi}", font=dict(size=16, color="#0f172a", family="Segoe UI")),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(255,255,255,1)",
                margin=dict(l=40, r=40, t=50, b=40),
                hovermode="x unified",
                xaxis=dict(showgrid=True, gridcolor="#f1f5f9", linecolor="#cbd5e1", dtick="M1", tickformat="%b %y"),
                yaxis=dict(showgrid=True, gridcolor="#e2e8f0", linecolor="#cbd5e1", title=uom),
                barmode='group',
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
            tab_content = dbc.Card([
                dbc.CardBody([
                    dcc.Graph(figure=fig, config={"displayModeBar": False})
                ])
            ], className="border-0 shadow-sm mt-3", style={"borderRadius": "12px"})
            
    else:  # Raw Table
        if not df_d_kpi.empty:
            df_table = df_d_kpi.copy()
            df_table['date'] = df_table['date'].dt.strftime("%Y-%m-%d")
            cols_to_show = ["date", "actual", "plan", "ucl", "cl", "lcl", "section", "sub_section", "source_file"]
            df_table = df_table[cols_to_show].sort_values("date", ascending=False)
            title_str = "Daily checking points raw data"
        elif not df_m_kpi.empty:
            df_table = df_m_kpi.copy()
            df_table['date'] = df_table['date'].dt.strftime("%Y-%m-%d")
            cols_to_show = ["date", "type", "value", "uom", "source_file"]
            df_table = df_table[cols_to_show].sort_values("date", ascending=False)
            title_str = "Monthly managing KPIs raw data"
        else:
            df_table = pd.DataFrame()
            title_str = "No data loaded"
            
        if df_table.empty:
            tab_content = dbc.Alert("No data records found.", color="warning", className="mt-3")
        else:
            tab_content = dbc.Card([
                dbc.CardBody([
                    html.H5(title_str, className="mb-3"),
                    dash_table.DataTable(
                        data=df_table.to_dict('records'),
                        columns=[{"name": i.upper(), "id": i} for i in df_table.columns],
                        page_size=15,
                        style_header={'backgroundColor': '#f8fafc', 'fontWeight': 'bold', 'color': '#0f172a'},
                        style_cell={'textAlign': 'left', 'padding': '10px', 'fontFamily': 'Segoe UI, Arial'},
                        style_data_conditional=[{
                            'if': {'row_index': 'odd'},
                            'backgroundColor': '#f8fafc'
                        }],
                        filter_action="native",
                        sort_action="native",
                        page_action="native"
                    )
                ])
            ], className="border-0 shadow-sm mt-3", style={"borderRadius": "12px"})
    return metrics_row, tab_content
"""

def analyze_chart_capabilities(df_kpi):
    """
    Analyzes the daily data columns/values and returns list of charts that can be plotted.
    """
    capabilities = []
    if df_kpi is None or df_kpi.empty:
        return capabilities
        
    cols = [str(c).lower().strip() for c in df_kpi.columns]
    
    # Helper to check if col has valid data
    def has_valid_col(name):
        actual_name = next((c for c in df_kpi.columns if str(c).lower().strip() == name), None)
        if actual_name is None:
            return False
        return df_kpi[actual_name].notna().any()
        
    # Check Sheet
    if 'date' in cols and has_valid_col('actual'):
        capabilities.append({
            "type": "Check Sheet",
            "x_recommend": "date",
            "y_recommend": "actual",
            "description": "Daily logging table of actuals, targets, limits, and operational status."
        })
        
    # Control Chart
    if 'date' in cols and has_valid_col('actual') and any(has_valid_col(x) for x in ['ucl', 'lcl', 'cl']):
        capabilities.append({
            "type": "Control Chart (SPC)",
            "x_recommend": "date",
            "y_recommend": "actual",
            "description": "Statistical process control run chart showing variance against control limits."
        })
        
    # Histogram
    if has_valid_col('actual'):
        actual_col = next((c for c in df_kpi.columns if str(c).lower().strip() == 'actual'), None)
        if actual_col and df_kpi[actual_col].dropna().count() >= 2:
            capabilities.append({
                "type": "Histogram",
                "x_recommend": "actual",
                "y_recommend": "frequency",
                "description": "Process data frequency distribution revealing shape and spread."
            })
            
    # Pareto
    if has_valid_col('actual') and has_valid_col('plan'):
        capabilities.append({
            "type": "Pareto Chart",
            "x_recommend": "date",
            "y_recommend": "deviation",
            "description": "Ranked absolute deviations from plan target to prioritize issues."
        })
        
    # Scatter
    if has_valid_col('plan') and has_valid_col('actual'):
        capabilities.append({
            "type": "Scatter Diagram",
            "x_recommend": "plan",
            "y_recommend": "actual",
            "description": "Correlation plot between plan targets and actual values with a trendline."
        })
        
    # Cause-and-Effect
    capabilities.append({
        "type": "Cause-and-Effect Diagram",
        "x_recommend": "None",
        "y_recommend": "None",
        "description": "Ishikawa / Fishbone root-cause brainstorming diagram for KPI deviations."
    })
    
    # Flowchart
    capabilities.append({
        "type": "Flowchart",
        "x_recommend": "None",
        "y_recommend": "None",
        "description": "Process workflow flowchart for daily management monitoring and actions."
    })
    
    return capabilities

def create_seven_charts(df_kpi, df_all_daily, kpi_name):
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    
    def get_target_series(df):
        if 'plan' in df.columns and 'actual' in df.columns:
            overlap = df['plan'].notna() & df['actual'].notna()
            if overlap.any():
                return df['plan']
        if 'cl' in df.columns and 'actual' in df.columns:
            overlap = df['cl'].notna() & df['actual'].notna()
            if overlap.any():
                return df['cl']
        if 'plan' in df.columns and df['plan'].notna().any():
            return df['plan']
        elif 'cl' in df.columns and df['cl'].notna().any():
            return df['cl']
        return pd.Series([np.nan] * len(df), index=df.index)
        
    # 0. Graceful empty data handling
    if df_kpi.empty:
        empty_fig = go.Figure()
        empty_fig.update_layout(title="No Data Available", height=300)
        return [empty_fig] * 7
        
    df_kpi = df_kpi.sort_values('date')
    dates = pd.to_datetime(df_kpi['date']).dt.strftime('%Y-%m-%d') if 'date' in df_kpi.columns else []
    actuals = df_kpi['actual'] if 'actual' in df_kpi.columns else pd.Series(dtype=float)
    plans = df_kpi['plan'] if 'plan' in df_kpi.columns else pd.Series(dtype=float)
    ucls = df_kpi['ucl'] if 'ucl' in df_kpi.columns else pd.Series([np.nan] * len(df_kpi))
    lcls = df_kpi['lcl'] if 'lcl' in df_kpi.columns else pd.Series([np.nan] * len(df_kpi))
    
    # --- CHART 1: Check Sheet ---
    statuses = []
    for act, pl, u, l in zip(actuals, plans, ucls, lcls):
        if pd.isna(act):
            statuses.append("N/A")
        elif pd.notna(u) and act > u:
            statuses.append("🔴 Out of Control (> UCL)")
        elif pd.notna(l) and act < l:
            statuses.append("🔴 Out of Control (< LCL)")
        elif pd.notna(pl):
            if act >= pl:
                statuses.append("🟢 On Target")
            else:
                statuses.append("🟡 Below Plan")
        else:
            statuses.append("🟢 Recorded")
            
    fig_check = go.Figure(data=[go.Table(
        header=dict(
            values=['Date', 'Actual', 'Plan', 'UCL', 'LCL', 'Status'],
            fill_color='#1e293b',
            align='center',
            font=dict(color='white', size=11, family="Segoe UI")
        ),
        cells=dict(
            values=[dates, actuals, plans, ucls, lcls, statuses],
            fill_color=[['#f8fafc', '#ffffff'] * (len(df_kpi) // 2 + 1)],
            align='center',
            font=dict(color='#0f172a', size=10, family="Segoe UI")
        )
    )])
    fig_check.update_layout(
        title=dict(text="1. Check Sheet (Daily Quality Log)", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        margin=dict(l=10, r=10, t=40, b=10),
        height=350
    )
    
    # --- CHART 2: Control Chart (SPC) ---
    fig_spc = go.Figure()
    if 'ucl' in df_kpi.columns and df_kpi['ucl'].notna().any():
        fig_spc.add_trace(go.Scatter(x=dates, y=df_kpi['ucl'], name="UCL", line=dict(color="#dc3545", width=1.5, dash="dot"), mode="lines"))
    if 'cl' in df_kpi.columns and df_kpi['cl'].notna().any():
        fig_spc.add_trace(go.Scatter(x=dates, y=df_kpi['cl'], name="CL", line=dict(color="#6c757d", width=1.5, dash="dash"), mode="lines"))
    if 'lcl' in df_kpi.columns and df_kpi['lcl'].notna().any():
        fig_spc.add_trace(go.Scatter(x=dates, y=df_kpi['lcl'], name="LCL", line=dict(color="#dc3545", width=1.5, dash="dot"), mode="lines"))
    if 'plan' in df_kpi.columns and df_kpi['plan'].notna().any():
        fig_spc.add_trace(go.Scatter(x=dates, y=df_kpi['plan'], name="Plan", line=dict(color="#198754", width=2, dash="dash"), mode="lines+markers"))
    if 'actual' in df_kpi.columns and df_kpi['actual'].notna().any():
        fig_spc.add_trace(go.Scatter(x=dates, y=df_kpi['actual'], name="Actual", line=dict(color="#0d6efd", width=3), marker=dict(size=8), mode="lines+markers"))

    fig_spc.update_layout(
        title=dict(text=f"2. Control Chart (SPC) - {kpi_name}", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=30, r=20, t=40, b=30),
        height=350,
        hovermode="x unified",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
    )
    
    # --- CHART 3: Histogram (Process Distribution) ---
    fig_hist = go.Figure()
    valid_actuals = df_kpi['actual'].dropna()
    if not valid_actuals.empty:
        fig_hist.add_trace(go.Histogram(
            x=valid_actuals,
            nbinsx=12,
            marker_color='#3b82f6',
            opacity=0.75,
            name="Actuals Frequency"
        ))
        # Add average line
        avg_val = valid_actuals.mean()
        if pd.notna(avg_val):
            fig_hist.add_vline(x=avg_val, line_dash="dash", line_color="#ef4444", line_width=2, 
                               annotation_text=f"Avg: {avg_val:.2f}", annotation_position="top right")

    fig_hist.update_layout(
        title=dict(text="3. Histogram (Process Distribution)", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=30, r=20, t=40, b=30),
        height=350,
        xaxis_title="Actual Value",
        yaxis_title="Frequency",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0")
    )
    
    # --- CHART 4: Pareto Chart (KPI Deviations from Plan) ---
    kpi_devs = []
    if not df_all_daily.empty:
        for k in df_all_daily['kpi_name'].unique():
            df_k = df_all_daily[df_all_daily['kpi_name'] == k]
            if 'actual' in df_k.columns:
                target_s = get_target_series(df_k)
                if target_s.notna().any():
                    dev = (df_k['actual'] - target_s).abs().sum()
                    if pd.notna(dev):
                        kpi_devs.append({"kpi": k, "deviation": dev})

    if kpi_devs:
        df_p = pd.DataFrame(kpi_devs).sort_values('deviation', ascending=False)
    else:
        # Fallback to date-wise deviation for this KPI
        df_k = df_kpi.copy()
        if 'actual' in df_k.columns:
            target_s = get_target_series(df_k)
            if target_s.notna().any():
                df_k['deviation'] = (df_k['actual'] - target_s).abs()
                df_p = df_k[['date', 'deviation']].rename(columns={'date': 'kpi'}).sort_values('deviation', ascending=False).head(10)
            else:
                df_p = pd.DataFrame(columns=["kpi", "deviation"])
        else:
            df_p = pd.DataFrame(columns=["kpi", "deviation"])

    if not df_p.empty:
        df_p['cumulative'] = df_p['deviation'].cumsum()
        total_dev = df_p['deviation'].sum()
        df_p['cum_pct'] = (df_p['cumulative'] / total_dev) * 100 if total_dev > 0 else 0.0
    else:
        df_p = pd.DataFrame([{"kpi": "No Data", "deviation": 0.0, "cum_pct": 0.0}])

    fig_pareto = go.Figure()
    fig_pareto.add_trace(go.Bar(
        x=df_p['kpi'],
        y=df_p['deviation'],
        name="Deviation Size",
        marker_color="#f59e0b"
    ))
    fig_pareto.add_trace(go.Scatter(
        x=df_p['kpi'],
        y=df_p['cum_pct'],
        name="Cumulative %",
        yaxis="y2",
        line=dict(color="#ef4444", width=2.5),
        mode="lines+markers"
    ))
    fig_pareto.update_layout(
        title=dict(text="4. Pareto Chart (KPI Deviations from Plan)", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=40, r=40, t=40, b=50),
        height=350,
        xaxis=dict(tickangle=30),
        yaxis=dict(title="Absolute Deviation"),
        yaxis2=dict(
            title="Cumulative %",
            overlaying="y",
            side="right",
            range=[0, 105],
            showgrid=False
        ),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
    )
    
    # --- CHART 5: Scatter Diagram (Actual vs Plan Correlation) ---
    fig_scatter = go.Figure()
    target_col = None
    if 'plan' in df_kpi.columns and 'actual' in df_kpi.columns and (df_kpi['plan'].notna() & df_kpi['actual'].notna()).any():
        target_col = 'plan'
    elif 'cl' in df_kpi.columns and 'actual' in df_kpi.columns and (df_kpi['cl'].notna() & df_kpi['actual'].notna()).any():
        target_col = 'cl'
    elif 'plan' in df_kpi.columns and df_kpi['plan'].notna().any():
        target_col = 'plan'
    elif 'cl' in df_kpi.columns and df_kpi['cl'].notna().any():
        target_col = 'cl'
        
    if target_col and 'actual' in df_kpi.columns:
        df_clean = df_kpi.dropna(subset=[target_col, 'actual'])
        if not df_clean.empty:
            target_label = "Plan" if target_col == 'plan' else "CL"
            fig_scatter.add_trace(go.Scatter(
                x=df_clean[target_col],
                y=df_clean['actual'],
                mode='markers',
                marker=dict(size=9, color='#8b5cf6', opacity=0.7),
                name=f'Actual vs {target_label}'
            ))
            
            # Target Line Y = X
            min_v = min(df_clean[target_col].min(), df_clean['actual'].min())
            max_v = max(df_clean[target_col].max(), df_clean['actual'].max())
            pad = (max_v - min_v) * 0.05 if max_v != min_v else 1.0
            min_v -= pad
            max_v += pad
            fig_scatter.add_trace(go.Scatter(
                x=[min_v, max_v],
                y=[min_v, max_v],
                mode='lines',
                line=dict(color='#64748b', dash='dash'),
                name='Ideal (Y=X)'
            ))
            
            # Regression line
            try:
                if len(df_clean) > 1:
                    coef = np.polyfit(df_clean[target_col], df_clean['actual'], 1)
                    poly1d_fn = np.poly1d(coef)
                    fig_scatter.add_trace(go.Scatter(
                        x=df_clean[target_col].sort_values(),
                        y=poly1d_fn(df_clean[target_col].sort_values()),
                        mode='lines',
                        line=dict(color='#3b82f6', width=2),
                        name=f'Trendline (r={np.corrcoef(df_clean[target_col], df_clean["actual"])[0,1]:.2f})'
                    ))
            except:
                pass

    target_title_label = "Plan" if target_col != 'cl' else "CL"
    fig_scatter.update_layout(
        title=dict(text=f"5. Scatter Diagram (Actual vs. {target_title_label})", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=30, r=20, t=40, b=30),
        height=350,
        xaxis_title=f"{target_title_label} Target",
        yaxis_title="Actual Value",
        xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
        yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=9))
    )
    
    # --- CHART 6: Cause-and-Effect Diagram (Fishbone) ---
    fig_fish = go.Figure()
    
    # Main horizontal spine
    fig_fish.add_trace(go.Scatter(
        x=[1, 8.5],
        y=[0, 0],
        mode='lines',
        line=dict(color='#0f172a', width=3),
        showlegend=False
    ))
    # Spine box
    fig_fish.add_trace(go.Scatter(
        x=[8.5, 9.7, 9.7, 8.5, 8.5],
        y=[-0.4, -0.4, 0.4, 0.4, -0.4],
        fill="toself",
        fillcolor="#f1f5f9",
        line=dict(color="#0f172a", width=2),
        mode="lines",
        showlegend=False
    ))
    fig_fish.add_annotation(
        x=9.1, y=0,
        text="<b>KPI Deviation</b>",
        showarrow=False,
        font=dict(size=10, color="#0f172a", family="Segoe UI")
    )
    # Arrow head
    fig_fish.add_annotation(
        x=8.5, y=0,
        ax=8.0, ay=0,
        xref="x", yref="y",
        axref="x", ayref="y",
        showarrow=True,
        arrowhead=2,
        arrowsize=1,
        arrowwidth=3,
        arrowcolor="#0f172a"
    )

    # Ribs and Causes
    ribs = [
        {"x": [2.5, 1.5], "y": [0, 2], "label": "People", "textpos": "top center", "causes": [
            {"x_offset": -0.3, "y": 0.7, "text": "Training Gap"},
            {"x_offset": -0.3, "y": 1.4, "text": "Fatigue / Shift"}
        ]},
        {"x": [5.0, 4.0], "y": [0, 2], "label": "Machine", "textpos": "top center", "causes": [
            {"x_offset": -0.3, "y": 0.7, "text": "Calibration"},
            {"x_offset": -0.3, "y": 1.4, "text": "Tool Wear"}
        ]},
        {"x": [7.5, 6.5], "y": [0, 2], "label": "Method", "textpos": "top center", "causes": [
            {"x_offset": -0.3, "y": 0.7, "text": "SOP Deviation"},
            {"x_offset": -0.3, "y": 1.4, "text": "Communication"}
        ]},
        {"x": [2.5, 1.5], "y": [0, -2], "label": "Material", "textpos": "bottom center", "causes": [
            {"x_offset": -0.3, "y": -0.7, "text": "Raw Spec Var"},
            {"x_offset": -0.3, "y": -1.4, "text": "Moisture Level"}
        ]},
        {"x": [5.0, 4.0], "y": [0, -2], "label": "Measurement", "textpos": "bottom center", "causes": [
            {"x_offset": -0.3, "y": -0.7, "text": "Sensor Delay"},
            {"x_offset": -0.3, "y": -1.4, "text": "Sampling Error"}
        ]},
        {"x": [7.5, 6.5], "y": [0, -2], "label": "Environment", "textpos": "bottom center", "causes": [
            {"x_offset": -0.3, "y": -0.7, "text": "Ambient Temp"},
            {"x_offset": -0.3, "y": -1.4, "text": "Dust / Humidity"}
        ]}
    ]

    for rib in ribs:
        # Draw rib
        fig_fish.add_trace(go.Scatter(
            x=rib["x"],
            y=rib["y"],
            mode='lines+text',
            line=dict(color='#475569', width=2),
            text=["", f"<b>{rib['label']}</b>"],
            textposition=rib["textpos"],
            textfont=dict(size=10, color='#0f172a', family="Segoe UI"),
            showlegend=False
        ))
        
        x_spine = rib["x"][0]
        x_tip = rib["x"][1]
        y_tip = rib["y"][1]
        
        for cause in rib["causes"]:
            y_c = cause["y"]
            x_intersect = x_spine + (y_c / y_tip) * (x_tip - x_spine)
            x_c_end = x_intersect - 0.7
            
            fig_fish.add_trace(go.Scatter(
                x=[x_intersect, x_c_end],
                y=[y_c, y_c],
                mode='lines+text',
                line=dict(color='#94a3b8', width=1),
                text=["", cause["text"]],
                textposition="top left",
                textfont=dict(size=8, color='#334155', family="Segoe UI"),
                showlegend=False
            ))

    fig_fish.update_layout(
        title=dict(text="6. Cause-and-Effect Diagram (Ishikawa / Fishbone)", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 10.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.5, 2.5])
    )
    
    # --- CHART 7: Flowchart (Process Workflow) ---
    fig_flow = go.Figure()
    
    steps = [
        {"x": 1.0, "y": 0, "text": "Define KPI &\nTargets", "shape": "rect"},
        {"x": 3.0, "y": 0, "text": "Measure &\nLog Daily Data", "shape": "rect"},
        {"x": 5.0, "y": 0, "text": "Compare with\nControl Limits", "shape": "rect"},
        {"x": 7.0, "y": 0, "text": "Out of\nControl?", "shape": "diamond"},
        {"x": 7.0, "y": -1.8, "text": "Perform RCA\n(Fishbone)", "shape": "rect"},
        {"x": 9.0, "y": -1.8, "text": "Implement\nActions", "shape": "rect"},
        {"x": 9.0, "y": 0, "text": "Standardise\n& Continue", "shape": "rect"}
    ]

    connections = [
        {"x": [1.5, 2.5], "y": [0, 0], "arrow": True, "label": ""},
        {"x": [3.5, 4.5], "y": [0, 0], "arrow": True, "label": ""},
        {"x": [5.5, 6.5], "y": [0, 0], "arrow": True, "label": ""},
        {"x": [7.0, 7.0], "y": [-0.4, -1.4], "arrow": True, "label": "Yes"},
        {"x": [7.6, 8.4], "y": [0, 0], "arrow": True, "label": "No"},
        {"x": [7.5, 8.5], "y": [-1.8, -1.8], "arrow": True, "label": ""},
        {"x": [9.0, 9.0], "y": [-1.4, -0.4], "arrow": True, "label": ""},
        {"x": [9.0, 9.5, 9.5, 3.0, 3.0], "y": [0, 0, 1.1, 1.1, 0.4], "arrow": True, "label": "Loop"}
    ]

    for conn in connections:
        fig_flow.add_trace(go.Scatter(
            x=conn["x"],
            y=conn["y"],
            mode='lines',
            line=dict(color='#475569', width=1.5),
            showlegend=False
        ))
        if conn["arrow"]:
            fig_flow.add_annotation(
                x=conn["x"][-1], y=conn["y"][-1],
                ax=conn["x"][-2] if len(conn["x"]) > 1 else conn["x"][0],
                ay=conn["y"][-2] if len(conn["y"]) > 1 else conn["y"][0],
                xref="x", yref="y",
                axref="x", ayref="y",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=1.5,
                arrowcolor="#475569"
            )
        if conn["label"]:
            mid_x = (conn["x"][0] + conn["x"][-1]) / 2
            mid_y = (conn["y"][0] + conn["y"][-1]) / 2
            fig_flow.add_annotation(
                x=mid_x, y=mid_y,
                text=conn["label"],
                showarrow=False,
                font=dict(size=8, color="#475569", family="Segoe UI"),
                bgcolor="white"
            )

    for step in steps:
        x = step["x"]
        y = step["y"]
        text = step["text"]
        
        if step["shape"] == "rect":
            fig_flow.add_trace(go.Scatter(
                x=[x-0.45, x+0.45, x+0.45, x-0.45, x-0.45],
                y=[y-0.35, y-0.35, y+0.35, y+0.35, y-0.35],
                fill="toself",
                fillcolor="#eff6ff",
                line=dict(color="#2563eb", width=2),
                mode="lines",
                showlegend=False
            ))
            fig_flow.add_annotation(
                x=x, y=y,
                text=text,
                showarrow=False,
                font=dict(size=8, color="#1e3a8a", family="Segoe UI")
            )
        elif step["shape"] == "diamond":
            fig_flow.add_trace(go.Scatter(
                x=[x, x+0.55, x, x-0.55, x],
                y=[y+0.45, y, y-0.45, y, y+0.45],
                fill="toself",
                fillcolor="#fef3c7",
                line=dict(color="#d97706", width=2),
                mode="lines",
                showlegend=False
            ))
            fig_flow.add_annotation(
                x=x, y=y,
                text=text,
                showarrow=False,
                font=dict(size=8, color="#78350f", family="Segoe UI")
            )

    fig_flow.update_layout(
        title=dict(text="7. Daily Management Process Flowchart", font=dict(size=14, color="#1e293b", family="Segoe UI")),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="white",
        margin=dict(l=10, r=10, t=40, b=10),
        height=350,
        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[0, 10.2]),
        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False, range=[-2.3, 1.6])
    )
    
    return [fig_check, fig_spc, fig_hist, fig_pareto, fig_scatter, fig_fish, fig_flow]

# -------------------------------------------------------------
# CALLBACK 3: Enable/Disable Uploader dynamically
# -------------------------------------------------------------
@app.callback(
    Output("dwm-upload-file", "style"),
    Output("dwm-upload-file", "children"),
    Input("dwm-upload-dept-input", "value")
)
def dwm_toggle_uploader(dept_value):
    try:
        with open("logs.txt", "a") as lf:
            lf.write(f"[DEBUG] dwm_toggle_uploader called with dept_value: {repr(dept_value)}\n")
    except Exception as e:
        pass

    if not dept_value or str(dept_value).strip() == "":
        style = {
            "width": "100%",
            "height": "38px",
            "lineHeight": "36px",
            "borderWidth": "1px",
            "borderStyle": "dashed",
            "borderRadius": "5px",
            "textAlign": "center",
            "cursor": "not-allowed",
            "backgroundColor": "#f1f5f9",
            "borderColor": "#cbd5e1",
            "color": "#64748b",
            "fontSize": "13px",
            "pointerEvents": "none"
        }
        children = html.Div(id="dwm-upload-file-label", children=[
            html.I(className="bi bi-lock-fill me-2"),
            "Enter department first to unlock upload"
        ])
        return style, children
    
    style = {
        "width": "100%",
        "height": "38px",
        "lineHeight": "36px",
        "borderWidth": "1px",
        "borderStyle": "dashed",
        "borderRadius": "5px",
        "textAlign": "center",
        "cursor": "pointer",
        "backgroundColor": "#f8fafc",
        "borderColor": "#0284c7",
        "color": "#0284c7",
        "fontSize": "13px",
        "fontWeight": "500",
        "pointerEvents": "auto"
    }
    children = html.Div(id="dwm-upload-file-label", children=[
        html.I(className="bi bi-cloud-arrow-up-fill me-2"),
        f"Upload Excel for {dept_value.strip()}"
    ])
    return style, children


# -------------------------------------------------------------
# CALLBACK 4: Switch Tabs
# -------------------------------------------------------------
def make_department_view(selected_dept):
    if not selected_dept:
        return html.Div([
            dbc.Alert("No departments loaded yet. Please click 'Upload Department' to upload your first DWM Excel sheet.", color="info", className="m-3")
        ], className="p-3")

    df_d = load_dwm_daily()
    df_d_filtered = df_d[df_d['department'] == selected_dept]
    
    uploaded_kpis = sorted(df_d_filtered['kpi_name'].dropna().unique().tolist()) if not df_d_filtered.empty else []
    
    if not uploaded_kpis:
        df_m = load_dwm_monthly()
        df_m_filtered = df_m[df_m['department'] == selected_dept]
        uploaded_kpis = sorted(df_m_filtered['kpi_name'].dropna().unique().tolist()) if not df_m_filtered.empty else []
        
    if not uploaded_kpis:
        return html.Div([
            dbc.Alert(f"No KPI data records found for '{selected_dept}'.", color="info")
        ], className="p-3")
        
    default_kpi = uploaded_kpis[0]
    
    return html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Select KPI to analyze:", style={"fontWeight": "600", "fontSize": "14px"}),
                dcc.Dropdown(
                    id="dwm-tab-kpi-dropdown",
                    options=[{"label": k, "value": k} for k in uploaded_kpis],
                    value=default_kpi,
                    clearable=False,
                    style={"fontSize": "13px"}
                )
            ], lg=4, md=6, xs=12, className="mb-4"),
            dbc.Col([
                dbc.Button(
                    "🗑️ Request Deletion",
                    id={"type": "dwm-request-delete-btn", "index": "delete"},
                    color="danger",
                    outline=True,
                    className="float-end mt-4",
                    style={"borderRadius": "8px", "fontWeight": "500"}
                )
            ], lg=8, md=6, xs=12, className="mb-4")
        ]),
        # Custom Chart Display Container (if configured)
        html.Div(id="dwm-custom-chart-display-container"),
        # 2-column grid for standard charts
        dbc.Row(id="dwm-tab-charts-grid")
    ])

@app.callback(
    Output("dwm-department-view-container", "children"),
    Input("dwm-dept-tabs", "active_tab")
)
def dwm_switch_tab(active_tab):
    return make_department_view(active_tab)

# -------------------------------------------------------------
# CALLBACK 5: Render Tab Charts
# -------------------------------------------------------------
@app.callback(
    Output("dwm-tab-charts-grid", "children"),
    Input("dwm-dept-tabs", "active_tab"),
    Input("dwm-tab-kpi-dropdown", "value")
)
def dwm_render_tab_charts(active_tab, selected_kpi):
    if not active_tab or not selected_kpi:
        return None
        
    df_d = load_dwm_daily()
    df_kpi = df_d[(df_d['department'] == active_tab) & (df_d['kpi_name'] == selected_kpi)]
    df_all_dept = df_d[df_d['department'] == active_tab]
    
    # Generate 7 charts
    figs = create_seven_charts(df_kpi, df_all_dept, selected_kpi)
    
    cols = []
    for idx, fig in enumerate(figs):
        col_width = 6
        if idx == 6: # flowchart full width
            col_width = 12
            
        cols.append(
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(figure=fig, config={"displayModeBar": False})
                    ])
                ], className="border-0 shadow-sm mb-4", style={"borderRadius": "12px", "overflow": "hidden"})
            ], lg=col_width, md=12, xs=12)
        )
        
    return cols


# -------------------------------------------------------------
# CALLBACK: Toggle Upload Department Modal
# -------------------------------------------------------------
@app.callback(
    Output("dwm-upload-dept-modal", "is_open"),
    Output("dwm-upload-dept-input", "value"),
    Output("dwm-instant-upload-status", "children", allow_duplicate=True),
    Input("dwm-upload-dept-btn", "n_clicks"),
    Input("dwm-upload-modal-close-btn", "n_clicks"),
    State("dwm-upload-dept-modal", "is_open"),
    prevent_initial_call=True
)
def dwm_toggle_upload_modal(open_clicks, close_clicks, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return is_open, dash.no_update, dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "dwm-upload-dept-btn":
        return True, "", ""
        
    if trigger_id == "dwm-upload-modal-close-btn":
        return False, dash.no_update, dash.no_update
        
    return is_open, dash.no_update, dash.no_update


# -------------------------------------------------------------
# CALLBACK 6: Handle File Upload, Parse, and Trigger Modal
# -------------------------------------------------------------
@app.callback(
    Output("dwm-instant-upload-status", "children"),
    Output("dwm-modal-data-store", "data"),
    Output("dwm-custom-chart-modal", "is_open"),
    Output("dwm-modal-chart-type", "options"),
    Output("dwm-modal-x-axis", "options"),
    Output("dwm-modal-y-axis", "options"),
    Output("dwm-dept-tabs", "children"),
    Output("dwm-dept-tabs", "active_tab"),
    Output("dwm-upload-dept-modal", "is_open", allow_duplicate=True),
    Input("dwm-upload-file", "contents"),
    State("dwm-upload-file", "filename"),
    State("dwm-upload-dept-input", "value"),
    State("dwm-dept-tabs", "children"),
    prevent_initial_call=True
)
def dwm_handle_upload(contents, filename, department, current_tabs):
    if contents is None or not department:
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
        
    try:
        content_type, content_string = contents.split(',', 1)
        decoded = base64.b64decode(content_string)
        
        suffix = Path(filename).suffix
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(decoded)
            tmp_name = tmp.name
            
        try:
            # 1. Convert Excel sheets to CSV in the background
            convert_excel_to_csvs_bg(tmp_name, department)
            
            # 2. Parse DWM Excel data
            df_m, df_d = parse_dwm_excel(tmp_name)
            
            if df_m.empty and df_d.empty:
                return (
                    dbc.Alert("No valid DWM daily or monthly data found in the uploaded file.", color="warning"),
                    dash.no_update, False, [], [], [], dash.no_update, dash.no_update, dash.no_update
                )
            
            # 3. Override department name with user entered department
            dept_name = department.strip()
            if not df_m.empty:
                df_m['department'] = dept_name
            if not df_d.empty:
                df_d['department'] = dept_name
                
            # 4. Upsert into consolidated CSV files
            upsert_dwm_data(df_m, df_d)
            
            # Save daily data to data store
            stored_data = df_d.to_dict('records') if not df_d.empty else []
            
            # 5. Analyze chart capabilities and columns
            capabilities = analyze_chart_capabilities(df_d)
            chart_options = [{"label": f"{c['type']} - {c['description']}", "value": c['type']} for c in capabilities]
            
            cols = df_d.columns.tolist() if not df_d.empty else []
            axis_options = [{"label": col, "value": col} for col in cols]
            
            # 6. Update Department Tabs dynamically
            df_m_all = load_dwm_monthly()
            df_d_all = load_dwm_daily()
            depts_m = df_m_all['department'].dropna().unique().tolist()
            depts_d = df_d_all['department'].dropna().unique().tolist()
            all_depts = sorted(list(set(depts_m + depts_d)))
            
            updated_tabs = [
                dbc.Tab(label=dept, tab_id=dept, tab_style={"cursor": "pointer"}) for dept in all_depts
            ]
            
            success_msg = f"Successfully uploaded and parsed '{filename}' for department '{dept_name}'! Please select custom axes in the popup to configure a custom chart."
            
            return (
                dbc.Alert(success_msg, color="success"),
                stored_data,
                True, # open modal
                chart_options,
                axis_options,
                axis_options,
                updated_tabs,
                dept_name, # activate new department tab
                False # close upload modal
            )
            
        finally:
            if os.path.exists(tmp_name):
                os.remove(tmp_name)
                
    except Exception as e:
        import traceback
        traceback.print_exc()
        return (
            dbc.Alert(f"An error occurred during file upload or parsing: {str(e)}", color="danger"),
            dash.no_update, False, [], [], [], dash.no_update, dash.no_update, dash.no_update
        )

# -------------------------------------------------------------
# CALLBACK 7: Modal Recommend Axes
# -------------------------------------------------------------
@app.callback(
    Output("dwm-modal-x-axis", "value"),
    Output("dwm-modal-y-axis", "value"),
    Input("dwm-modal-chart-type", "value"),
    State("dwm-modal-data-store", "data"),
    prevent_initial_call=True
)
def dwm_modal_recommend_axes(chart_type, stored_data):
    if not chart_type or not stored_data:
        return dash.no_update, dash.no_update
        
    df = pd.DataFrame(stored_data)
    
    # Helper to find case-insensitive column match
    def find_col(name):
        return next((c for c in df.columns if str(c).lower().strip() == name), None)
        
    x_val = None
    y_val = None
    
    if chart_type == "Check Sheet":
        x_val = find_col("date")
        y_val = find_col("actual")
    elif chart_type == "Control Chart (SPC)":
        x_val = find_col("date")
        y_val = find_col("actual")
    elif chart_type == "Histogram":
        x_val = find_col("actual")
        y_val = None
    elif chart_type == "Pareto Chart":
        x_val = find_col("date")
        y_val = find_col("actual")
    elif chart_type == "Scatter Diagram":
        x_val = find_col("plan")
        y_val = find_col("actual")
        
    return x_val, y_val

# -------------------------------------------------------------
# CALLBACK 8: Modal Actions
# -------------------------------------------------------------
@app.callback(
    Output("dwm-custom-chart-modal", "is_open", allow_duplicate=True),
    Output("dwm-custom-chart-store", "data"),
    Input("dwm-modal-cancel-btn", "n_clicks"),
    Input("dwm-modal-generate-btn", "n_clicks"),
    State("dwm-modal-chart-type", "value"),
    State("dwm-modal-x-axis", "value"),
    State("dwm-modal-y-axis", "value"),
    prevent_initial_call=True
)
def dwm_modal_footer_actions(cancel_clicks, generate_clicks, chart_type, x_axis, y_axis):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    if trigger_id == "dwm-modal-cancel-btn":
        return False, dash.no_update
        
    if trigger_id == "dwm-modal-generate-btn":
        config = {
            "chart_type": chart_type,
            "x_axis": x_axis,
            "y_axis": y_axis
        }
        return False, config
        
    return dash.no_update, dash.no_update

# -------------------------------------------------------------
# CALLBACK 9: Render Custom Chart
# -------------------------------------------------------------
@app.callback(
    Output("dwm-custom-chart-display-container", "children"),
    Input("dwm-dept-tabs", "active_tab"),
    Input("dwm-tab-kpi-dropdown", "value"),
    Input("dwm-custom-chart-store", "data")
)
def dwm_render_custom_chart(active_tab, selected_kpi, custom_config):
    if not active_tab or active_tab == "tab-upload" or not selected_kpi or not custom_config:
        return None
        
    chart_type = custom_config.get("chart_type")
    x_col = custom_config.get("x_axis")
    y_col = custom_config.get("y_axis")
    
    if not chart_type or not x_col or not y_col:
        return None
        
    df_d = load_dwm_daily()
    df_kpi = df_d[(df_d['department'] == active_tab) & (df_d['kpi_name'] == selected_kpi)].sort_values('date')
    
    if df_kpi.empty:
        return None
        
    fig = go.Figure()
    
    if chart_type == "Check Sheet":
        statuses = []
        actuals = df_kpi[y_col] if y_col in df_kpi.columns else pd.Series([np.nan] * len(df_kpi))
        plans = df_kpi['plan'] if 'plan' in df_kpi.columns else pd.Series([np.nan] * len(df_kpi))
        dates = df_kpi[x_col] if x_col in df_kpi.columns else pd.Series([""] * len(df_kpi))
        
        for act, pl in zip(actuals, plans):
            if pd.isna(act):
                statuses.append("N/A")
            elif pd.notna(pl):
                if act >= pl:
                    statuses.append("🟢 On Target")
                else:
                    statuses.append("🟡 Below Plan")
            else:
                statuses.append("🟢 Recorded")
                
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=[str(x_col).upper(), str(y_col).upper(), 'PLAN', 'STATUS'],
                fill_color='#0284c7',
                align='center',
                font=dict(color='white', size=12, family="Segoe UI")
            ),
            cells=dict(
                values=[dates, actuals, plans, statuses],
                fill_color=[['#f8fafc', '#ffffff'] * (len(df_kpi) // 2 + 1)],
                align='center',
                font=dict(color='#0f172a', size=11, family="Segoe UI")
            )
        )])
        fig.update_layout(height=350, margin=dict(l=10, r=10, t=10, b=10))
        
    elif chart_type == "Control Chart (SPC)":
        for col in ['ucl', 'cl', 'lcl']:
            if col in df_kpi.columns and df_kpi[col].notna().any():
                color = "#dc3545" if col != "cl" else "#6c757d"
                dash_style = "dot" if col != "cl" else "dash"
                fig.add_trace(go.Scatter(x=df_kpi[x_col], y=df_kpi[col], name=col.upper(), line=dict(color=color, width=1.5, dash=dash_style), mode="lines"))
        
        if 'plan' in df_kpi.columns and df_kpi['plan'].notna().any():
            fig.add_trace(go.Scatter(x=df_kpi[x_col], y=df_kpi['plan'], name="Plan", line=dict(color="#198754", width=2, dash="dash"), mode="lines+markers"))
            
        fig.add_trace(go.Scatter(x=df_kpi[x_col], y=df_kpi[y_col], name=str(y_col).upper(), line=dict(color="#0284c7", width=3), marker=dict(size=8), mode="lines+markers"))
        
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="white",
            margin=dict(l=30, r=20, t=20, b=30),
            height=350,
            hovermode="x unified",
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
    elif chart_type == "Histogram":
        fig.add_trace(go.Histogram(
            x=df_kpi[x_col].dropna(),
            nbinsx=12,
            marker_color='#3b82f6',
            opacity=0.75
        ))
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="white",
            margin=dict(l=30, r=20, t=20, b=30),
            height=350,
            xaxis_title=str(x_col).upper(),
            yaxis_title="Frequency",
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0")
        )
        
    elif chart_type == "Pareto Chart":
        df_kpi = df_kpi.copy()
        if x_col in df_kpi.columns and y_col in df_kpi.columns:
            df_kpi['deviation'] = (df_kpi[y_col] - df_kpi['plan']).abs() if 'plan' in df_kpi.columns else df_kpi[y_col]
            df_p = df_kpi.sort_values('deviation', ascending=False).head(10)
            df_p['cumulative'] = df_p['deviation'].cumsum()
            total_dev = df_p['deviation'].sum()
            df_p['cum_pct'] = (df_p['cumulative'] / total_dev) * 100 if total_dev > 0 else 0.0
            
            fig.add_trace(go.Bar(x=df_p[x_col], y=df_p['deviation'], name="Deviation Size", marker_color="#f59e0b"))
            fig.add_trace(go.Scatter(x=df_p[x_col], y=df_p['cum_pct'], name="Cumulative %", yaxis="y2", line=dict(color="#ef4444", width=2.5), mode="lines+markers"))
            
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="white",
                margin=dict(l=40, r=40, t=20, b=50),
                height=350,
                xaxis=dict(tickangle=30),
                yaxis=dict(title="Deviation"),
                yaxis2=dict(title="Cumulative %", overlaying="y", side="right", range=[0, 105], showgrid=False),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            
    elif chart_type == "Scatter Diagram":
        df_clean = df_kpi.dropna(subset=[x_col, y_col])
        if not df_clean.empty:
            fig.add_trace(go.Scatter(x=df_clean[x_col], y=df_clean[y_col], mode='markers', marker=dict(size=10, color='#8b5cf6', opacity=0.7), name='Points'))
            try:
                if len(df_clean) > 1:
                    coef = np.polyfit(df_clean[x_col], df_clean[y_col], 1)
                    poly1d_fn = np.poly1d(coef)
                    fig.add_trace(go.Scatter(
                        x=df_clean[x_col].sort_values(),
                        y=poly1d_fn(df_clean[x_col].sort_values()),
                        mode='lines',
                        line=dict(color='#3b82f6', width=2),
                        name='Trendline'
                    ))
            except:
                pass
                
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="white",
            margin=dict(l=30, r=20, t=20, b=30),
            height=350,
            xaxis_title=str(x_col).upper(),
            yaxis_title=str(y_col).upper(),
            xaxis=dict(showgrid=True, gridcolor="#f1f5f9"),
            yaxis=dict(showgrid=True, gridcolor="#e2e8f0"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        
    elif chart_type == "Cause-and-Effect Diagram":
        empty_fig = create_seven_charts(df_kpi, pd.DataFrame(), selected_kpi)[5]
        fig = empty_fig
        
    elif chart_type == "Flowchart":
        empty_fig = create_seven_charts(df_kpi, pd.DataFrame(), selected_kpi)[6]
        fig = empty_fig
        
    return dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader(html.H5(f"⭐ Custom Configured Chart: {chart_type} ({y_col} vs {x_col})", className="text-success mb-0", style={"fontWeight": "bold"})),
                dbc.CardBody([
                    dcc.Graph(figure=fig, config={"displayModeBar": False})
                ])
            ], className="border-0 shadow-sm mb-4", style={"borderRadius": "12px", "border": "2px solid #22c55e", "overflow": "hidden"})
        ], width=12)
    ])


def save_delete_request(dept_name):
    import csv
    from datetime import datetime
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    req_file = DATA_DIR / "dwm_delete_requests.csv"
    
    # Check if file exists, if not write header
    file_exists = req_file.exists()
    
    # Read existing requests to check for pending
    if file_exists:
        try:
            df = pd.read_csv(req_file)
            pending = df[(df['department'] == dept_name) & (df['status'] == 'Pending')]
            if not pending.empty:
                return False, f"A deletion request is already pending for '{dept_name}'."
        except Exception as e:
            print(f"Error reading delete requests CSV: {e}")
            
    # Append the new request
    try:
        with open(req_file, mode='a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(['department', 'requested_at', 'status'])
            writer.writerow([dept_name, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), 'Pending'])
        return True, f"Deletion request for department '{dept_name}' successfully submitted to Admin."
    except Exception as e:
        return False, f"Error saving deletion request: {e}"

# -------------------------------------------------------------
# CALLBACK 10: Handle Deletion Modal & Request Submission
# -------------------------------------------------------------
# -------------------------------------------------------------
# CALLBACK 10: Handle Deletion Modal & Request Submission
# -------------------------------------------------------------
@app.callback(
    Output("dwm-delete-confirm-modal", "is_open"),
    Output("dwm-delete-confirm-text", "children"),
    Output("dwm-delete-notification-container", "children"),
    Input({"type": "dwm-request-delete-btn", "index": ALL}, "n_clicks"),
    Input("dwm-delete-confirm-cancel", "n_clicks"),
    Input("dwm-delete-confirm-send", "n_clicks"),
    State("dwm-dept-tabs", "active_tab"),
    State("dwm-delete-confirm-modal", "is_open"),
    prevent_initial_call=True
)
def dwm_handle_delete_modal(req_clicks, cancel_clicks, send_clicks, active_tab, is_open):
    ctx = dash.callback_context
    if not ctx.triggered:
        return False, "", dash.no_update
        
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    is_delete_req = False
    if "dwm-request-delete-btn" in trigger_id and req_clicks and any(c is not None for c in req_clicks):
        is_delete_req = True
        
    if is_delete_req:
        return True, f"Are you sure you want to request the deletion of the department '{active_tab}'?", dash.no_update
        
    if trigger_id == "dwm-delete-confirm-cancel" and cancel_clicks:
        return False, "", dash.no_update
        
    if trigger_id == "dwm-delete-confirm-send" and send_clicks:
        success, msg = save_delete_request(active_tab)
        color = "success" if success else "warning"
        alert = dbc.Alert(msg, color=color, dismissable=True, duration=5000, style={"borderRadius": "8px"})
        return False, "", alert
        
    return is_open, dash.no_update, dash.no_update




