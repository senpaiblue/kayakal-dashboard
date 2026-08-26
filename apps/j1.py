import dash
from app import app
import pandas as pd
from pathlib import Path
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

CSV_PATH = "./Data/j1_data.csv"

def read_csv_safely(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to read CSV with any known encoding. Convert file to UTF-8 or CP1252.")

def load_fresh_data():
    """Load fresh data from CSV - called in each callback to get latest data"""
    if not Path(CSV_PATH).exists():
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    
    df = read_csv_safely(CSV_PATH)
    df.columns = df.columns.str.strip()
    # Strip whitespace from all string cell values so groupby never produces
    # duplicate entries from "Services" vs "Services " style differences
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].str.strip()
    return df

# Initial load for layout only
try:
    df = load_fresh_data()
    # Get unique zones and departments
    zones = sorted([z for z in df["Zone"].dropna().unique() if str(z).strip()]) if "Zone" in df.columns else []
    departments = sorted([d for d in df["Department"].dropna().unique() if str(d).strip()]) if "Department" in df.columns else []
except:
    zones = []
    departments = []

layout = html.Div([
    html.H2("J1+", style={"marginBottom": "20px", "color": "#0d6efd"}),
    
    # NEW: Employee ID status check section
    html.Div([
        html.H4("Check Employee Status", style={"marginBottom": "15px", "color": "#333", "fontSize": "16px"}),
        html.Div([
            dbc.Input(id="j1-emp-id-input", type="text", placeholder="Enter Employee ID...", style={"width": "300px", "display": "inline-block", "marginRight": "10px"}),
            dbc.Button("Check Status", id="j1-emp-id-btn", color="primary", style={"display": "inline-block", "verticalAlign": "baseline"}),
        ], style={"marginBottom": "10px"}),
        html.Div(id="j1-emp-status-output", style={"marginTop": "5px", "minHeight": "20px"})
    ], style={"marginBottom": "20px", "padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "border": "1px solid #ddd"}),
    
    # Filters Row: Zone and Department
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Zone", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="j1-zone-dropdown",
                    options=[{"label": "All", "value": "All"}] + [{"label": z, "value": z} for z in zones],
                    value="All",
                    clearable=False
                )
            ], width=6),
            dbc.Col([
                html.Label("Department", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="j1-department-dropdown",
                    options=[{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments],
                    value="All",
                    clearable=False
                )
            ], width=6),
        ]),
    ], className="j1-filter-row", style={"marginBottom": "20px", "display": "block", "width": "100%"}),
    
    html.Hr(style={"margin": "20px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Graph 1: Trend graph - day-wise how many people gave exam
    dbc.Row([
        dbc.Col([
            html.H4("Daily Exam Attempts Trend", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="j1-trend-graph", style={"height": "400px"})
        ], width=12)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # NEW Graph: Date vs No of people registered
    dbc.Row([
        dbc.Col([
            html.H4("Date vs No of People Registered", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="j1-registered-by-date-graph", style={"height": "400px"})
        ], width=12)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Graph 2: Zone-wise cleared exam with details below graph
    dbc.Row([
        dbc.Col([
            html.H4("Zone-wise Exam Clearance", style={"marginBottom": "15px", "color": "#333"}),
            dcc.Graph(id="j1-zone-cleared-graph", style={"height": "500px"})
        ], width=12)
    ], style={"marginTop": "20px"}),
    dbc.Row([
        dbc.Col([
            html.Div(id="j1-zone-summary", style={"padding": "10px"}),
            html.Div([
                html.H5("Cleared Exam Details", style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "10px"}),
                html.P("Use column filter boxes to narrow results, then export to Excel.",
                       style={"fontSize": "11px", "color": "#666", "marginBottom": "8px"}),
                dash_table.DataTable(
                    id="j1-zone-detail-table",
                    data=[], columns=[],
                    filter_action="native",
                    export_format="xlsx", export_headers="display",
                    page_action="native", page_size=10,
                    style_table={"overflowX": "auto", "overflowY": "auto"},
                    style_cell={"textAlign": "left", "padding": "8px", "fontSize": "11px", "whiteSpace": "normal", "height": "auto"},
                    style_header={"backgroundColor": "#0d6efd", "color": "white", "fontWeight": "bold", "fontSize": "12px"},
                    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}],
                )
            ], id="j1-zone-table-wrapper", style={"display": "none", "padding": "0 10px"})
        ], width=12)
    ]),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Graph 3: Department-wise cleared exam with details below graph
    dbc.Row([
        dbc.Col([
            html.H4("Department-wise Exam Clearance", style={"marginBottom": "15px", "color": "#333"}),
            dcc.Graph(id="j1-dept-cleared-graph", style={"height": "800px"})
        ], width=12)
    ], style={"marginTop": "20px"}),
    dbc.Row([
        dbc.Col([
            html.Div(id="j1-dept-summary", style={"padding": "10px"}),
            html.Div([
                html.H5("Cleared Exam Details", style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "10px"}),
                html.P("Use column filter boxes to narrow results, then export to Excel.",
                       style={"fontSize": "11px", "color": "#666", "marginBottom": "8px"}),
                dash_table.DataTable(
                    id="j1-dept-detail-table",
                    data=[], columns=[],
                    filter_action="native",
                    export_format="xlsx", export_headers="display",
                    page_action="native", page_size=10,
                    style_table={"overflowX": "auto", "overflowY": "auto"},
                    style_cell={"textAlign": "left", "padding": "8px", "fontSize": "11px", "whiteSpace": "normal", "height": "auto"},
                    style_header={"backgroundColor": "#0d6efd", "color": "white", "fontWeight": "bold", "fontSize": "12px"},
                    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}],
                )
            ], id="j1-dept-table-wrapper", style={"display": "none", "padding": "0 10px"})
        ], width=12)
    ], style={"marginBottom": "10px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Graph 4: Grade-wise cleared exam with details below graph
    dbc.Row([
        dbc.Col([
            html.H4("Grade-wise Exam Clearance", style={"marginBottom": "15px", "color": "#333"}),
            dcc.Graph(id="j1-grade-cleared-graph", style={"height": "500px"})
        ], width=12)
    ], style={"marginTop": "20px"}),
    dbc.Row([
        dbc.Col([
            html.Div(id="j1-grade-summary", style={"padding": "10px"}),
            html.Div([
                html.H5("Cleared Exam Details", style={"fontSize": "14px", "fontWeight": "600", "marginBottom": "10px"}),
                html.P("Use column filter boxes to narrow results, then export to Excel.",
                       style={"fontSize": "11px", "color": "#666", "marginBottom": "8px"}),
                dash_table.DataTable(
                    id="j1-grade-detail-table",
                    data=[], columns=[],
                    filter_action="native",
                    export_format="xlsx", export_headers="display",
                    page_action="native", page_size=10,
                    style_table={"overflowX": "auto", "overflowY": "auto"},
                    style_cell={"textAlign": "left", "padding": "8px", "fontSize": "11px", "whiteSpace": "normal", "height": "auto"},
                    style_header={"backgroundColor": "#0d6efd", "color": "white", "fontWeight": "bold", "fontSize": "12px"},
                    style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#f8f9fa"}],
                )
            ], id="j1-grade-table-wrapper", style={"display": "none", "padding": "0 10px"})
        ], width=12)
    ]),
    
    # Interval component to refresh dropdowns every 5 seconds
    dcc.Interval(
        id='j1-interval-refresh',
        interval=5*1000,  # in milliseconds (5 seconds)
        n_intervals=0
    )
    
], style={"padding": "20px", "fontFamily": "Arial"})

@app.callback(
    Output("j1-zone-dropdown", "options"),
    Input("j1-interval-refresh", "n_intervals")
)
def refresh_j1_zone_dropdown(n_intervals):
    try:
        df = load_fresh_data()
        
        # Get unique zones
        zones = sorted([z for z in df["Zone"].dropna().unique() if str(z).strip()]) if "Zone" in df.columns else []
        zone_options = [{"label": "All", "value": "All"}] + [{"label": z, "value": z} for z in zones]
        
        return zone_options
    except:
        return [{"label": "All", "value": "All"}]

# Callback to update department dropdown based on zone selection and interval refresh
@app.callback(
    Output("j1-department-dropdown", "options"),
    Output("j1-department-dropdown", "value"),
    Input("j1-interval-refresh", "n_intervals"),
    Input("j1-zone-dropdown", "value"),
    State("j1-department-dropdown", "value")
)
def update_j1_department_options_j1(n_intervals, selected_zone, current_dept_value):
    try:
        df = load_fresh_data()
        departments = sorted([d for d in df["Department"].dropna().unique() if str(d).strip()]) if "Department" in df.columns else []

        if selected_zone == "All" or selected_zone is None:
            dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments]
            valid_values = {opt["value"] for opt in dept_options}
            next_value = current_dept_value if current_dept_value in valid_values else "All"
            return dept_options, next_value
        else:
            if "Department" in df.columns and "Zone" in df.columns:
                filtered_depts = df[df["Zone"] == selected_zone]["Department"].dropna().unique()
                filtered_depts = sorted([d for d in filtered_depts if str(d).strip()])
                dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in filtered_depts]
                valid_values = {opt["value"] for opt in dept_options}
                next_value = current_dept_value if current_dept_value in valid_values else "All"
                return dept_options, next_value
            else:
                dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments]
                valid_values = {opt["value"] for opt in dept_options}
                next_value = current_dept_value if current_dept_value in valid_values else "All"
                return dept_options, next_value
    except:
        fallback_options = [{"label": "All", "value": "All"}]
        fallback_value = current_dept_value if current_dept_value == "All" else "All"
        return fallback_options, fallback_value

# Callback for trend graph - day-wise exam attempts
@app.callback(
    Output("j1-trend-graph", "figure"),
    Input("j1-zone-dropdown", "value"),
    Input("j1-department-dropdown", "value"),
    Input("j1-interval-refresh", "n_intervals"),
)
def update_j1_trend_graph(selected_zone, selected_dept, n_intervals):
    try:
        df = load_fresh_data()
        filtered_df = df.copy()
        
        # Apply filters
        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
        
        # Check if we have date column (could be "Attempted on" or similar)
        date_col = None
        for col in df.columns:
            if "attempt" in col.lower() or "date" in col.lower():
                date_col = col
                break
        
        if date_col is None or date_col not in filtered_df.columns:
            return go.Figure().add_annotation(
                text="No date column found for trend analysis",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        # Parse dates and count by day
        try:
            filtered_df[date_col] = pd.to_datetime(filtered_df[date_col], errors='coerce')
            filtered_df = filtered_df.dropna(subset=[date_col])
            
            daily_counts = filtered_df.groupby(filtered_df[date_col].dt.date).size().reset_index(name="Count")
            daily_counts = daily_counts.sort_values(date_col)
            
            fig = go.Figure(data=[go.Scatter(
                x=daily_counts[date_col],
                y=daily_counts["Count"],
                mode='lines+markers',
                marker=dict(size=8, color="#0d6efd"),
                line=dict(width=2, color="#0d6efd"),
                hovertemplate="<b>Date:</b> %{x}<br><b>Attempts:</b> %{y}<extra></extra>"
            )])
            
            fig.update_layout(
                title=dict(
                    text="<b>Daily Exam Attempts Trend</b>",
                    x=0.5,
                    xanchor='center',
                    font=dict(size=18, color="#2c3e50")
                ),
                xaxis_title="Date",
                yaxis_title="Number of Exam Attempts",
                plot_bgcolor="rgba(240,240,240,0.3)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=50, r=40, t=60, b=40),
                height=400,
                font=dict(size=13),
                xaxis=dict(
                    gridcolor='rgba(200,200,200,0.3)',
                    showgrid=True
                ),
                yaxis=dict(
                    gridcolor='rgba(200,200,200,0.3)',
                    showgrid=True
                )
            )
            
            return fig
        except Exception as e:
            return go.Figure().add_annotation(
                text=f"Error processing dates: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error loading data: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )

# NEW callback: Date vs No of people registered (only)
@app.callback(
    Output("j1-registered-by-date-graph", "figure"),
    Input("j1-zone-dropdown", "value"),
    Input("j1-department-dropdown", "value"),
    Input("j1-interval-refresh", "n_intervals"),
)
def update_j1_registered_by_date_graph(selected_zone, selected_dept, n_intervals):
    try:
        df = load_fresh_data()
        filtered_df = df.copy()

        # Apply filters
        if selected_zone != "All" and "Zone" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]

        # Department column for J1 attended sheet
        dept_col = "Department" if "Department" in filtered_df.columns else None
        if selected_dept != "All" and dept_col:
            filtered_df = filtered_df[filtered_df[dept_col] == selected_dept]

        date_col = "Date" if "Date" in filtered_df.columns else None
        reg_col = None
        for col in filtered_df.columns:
            if "no of people" in col.lower() and "regis" in col.lower():
                reg_col = col
                break

        if not date_col or not reg_col:
            return go.Figure().add_annotation(
                text="Required columns not found (need Date and No of people regisered)",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )

        # Parse date and registration counts
        tmp = filtered_df[[date_col, reg_col]].copy()
        tmp[date_col] = pd.to_datetime(tmp[date_col], errors="coerce")
        tmp[reg_col] = pd.to_numeric(tmp[reg_col], errors="coerce")
        tmp = tmp.dropna(subset=[date_col])

        if tmp.empty:
            return go.Figure().add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )

        # In the source sheet, the registered count is often present only once per day.
        # Use max per day to pick the value.
        daily = tmp.groupby(tmp[date_col].dt.date)[reg_col].max().fillna(0).reset_index()
        daily.columns = ["Date", "Registered"]
        daily = daily.sort_values("Date")

        fig = go.Figure(data=[go.Bar(
            x=daily["Date"],
            y=daily["Registered"],
            marker=dict(color="#0d6efd"),
            hovertemplate="<b>Date:</b> %{x}<br><b>Registered:</b> %{y}<extra></extra>"
        )])

        fig.update_layout(
            title=dict(
                text="<b>Date vs No of People Registered</b>",
                x=0.5,
                xanchor="center",
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Date",
            yaxis_title="No of People Registered",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=50, r=40, t=60, b=40),
            height=400,
            font=dict(size=13),
            xaxis=dict(gridcolor="rgba(200,200,200,0.3)", showgrid=True),
            yaxis=dict(gridcolor="rgba(200,200,200,0.3)", showgrid=True),
        )

        return fig
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )

# Callback for zone-wise cleared exam graph
@app.callback(
    Output("j1-zone-cleared-graph", "figure"),
    Input("j1-zone-dropdown", "value"),
    Input("j1-department-dropdown", "value"),
)
def update_j1_zone_cleared_graph(selected_zone, selected_dept):
    try:
        df = load_fresh_data()
        filtered_df = df.copy()
        
        # Apply filters
        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
        
        # Check for cleared status (J1 uses Status as grade: PASS/FAIL/SILVER/BRONZE/PLATINUM)
        status_col = None
        for col in df.columns:
            if "status" in col.lower() or "result" in col.lower() or "cleared" in col.lower():
                status_col = col
                break
        
        # If we don't have a status column, fall back to using ALL records
        # so that the chart still shows useful information.
        if status_col and "Zone" in filtered_df.columns:
            s = filtered_df[status_col].astype(str).str.strip().str.upper()
            cleared_df = filtered_df[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]
            title_suffix = " (Cleared Only)"
        elif "Zone" in filtered_df.columns:
            cleared_df = filtered_df
            title_suffix = " (All Records - no status column)"
        else:
            return go.Figure().add_annotation(
                text="No zone data found",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        if cleared_df.empty:
            return go.Figure().add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        # Count by zone
        zone_counts = cleared_df.groupby("Zone").size().reset_index(name="Count")
        zone_counts = zone_counts.sort_values("Count", ascending=True)
        
        fig = go.Figure(data=[go.Bar(
            y=zone_counts["Zone"],
            x=zone_counts["Count"],
            orientation='h',
            marker=dict(color="#27ae60"),
            text=zone_counts["Count"],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{y}</b><br>Cleared: %{x}<extra></extra>"
        )])
        
        fig.update_layout(
            title=dict(
                text=f"<b>Zone-wise Exam Clearance{title_suffix}</b>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Number of People Cleared",
            yaxis_title="",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=150, r=40, t=60, b=40),
            height=500,
            font=dict(size=13),
            xaxis=dict(
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True
            ),
            yaxis=dict(
                tickfont=dict(size=13)
            )
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )

# Callback to show zone details when clicked
@app.callback(
    Output("j1-zone-summary", "children"),
    Output("j1-zone-detail-table", "data"),
    Output("j1-zone-detail-table", "columns"),
    Output("j1-zone-table-wrapper", "style"),
    Input("j1-zone-cleared-graph", "clickData"),
    State("j1-zone-dropdown", "value"),
    State("j1-department-dropdown", "value"),
)
def show_j1_zone_details(clickData, selected_zone, selected_dept):
    _hidden = {"display": "none", "padding": "0 10px"}
    _shown  = {"display": "block", "padding": "0 10px"}
    try:
        df = load_fresh_data()

        if clickData is None:
            placeholder = html.Div([
                html.H5("Zone Details", style={"color": "#666", "textAlign": "center", "marginTop": "50px"}),
                html.P("Click on a zone in the graph to see details",
                       style={"textAlign": "center", "color": "#999", "fontSize": "14px"})
            ])
            return placeholder, [], [], _hidden

        zone = clickData["points"][0]["y"]
        filtered_df = df.copy()

        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]

        status_col = None
        for col in df.columns:
            if "status" in col.lower() or "result" in col.lower() or "cleared" in col.lower():
                status_col = col
                break

        zone_data = filtered_df[filtered_df["Zone"] == zone]
        if status_col:
            s = zone_data[status_col].astype(str).str.strip().str.upper()
            zone_data = zone_data[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]

        if zone_data.empty:
            return html.Div([html.H5(f"No cleared data for {zone}", style={"color": "#666"})]), [], [], _hidden

        grade_col = "Status" if "Status" in df.columns else None
        total_cleared = len(zone_data)
        grade_counts = {}
        if grade_col and grade_col in zone_data.columns:
            grade_counts = zone_data[grade_col].value_counts().to_dict()

        display_columns = []
        for col in ["Name", "Employee ID", "Department", "Zone"]:
            if col in zone_data.columns:
                display_columns.append(col)
        if grade_col:
            display_columns.append(grade_col)
        available_columns = [col for col in display_columns if col in zone_data.columns]

        summary = html.Div([
            html.H4(f"{zone}", style={"color": "#0d6efd", "marginBottom": "15px", "fontSize": "18px"}),
            html.Div([
                html.Div([
                    html.Div("Total Cleared", style={"fontSize": "12px", "color": "#666"}),
                    html.Div(f"{total_cleared}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0d6efd"})
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "10px"}),
                html.Div([
                    html.Div("Grade Breakdown", style={"fontSize": "12px", "color": "#666", "marginBottom": "8px", "fontWeight": "600"}),
                    html.Div([
                        html.Div([
                            html.Span(f"{g}: ", style={"fontSize": "11px", "fontWeight": "600"}),
                            html.Span(f"{c}", style={"fontSize": "11px", "color": "#0d6efd"})
                        ], style={"marginBottom": "4px"}) for g, c in grade_counts.items()
                    ]) if grade_counts else html.P("No grade data available", style={"fontSize": "11px", "color": "#999"})
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "15px"})
            ])
        ])

        return (
            summary,
            zone_data[available_columns].fillna("N/A").to_dict("records"),
            [{"name": col, "id": col} for col in available_columns],
            _shown
        )
    except Exception as e:
        return html.Div([html.P(f"Error: {str(e)}", style={"color": "#e74c3c"})]), [], [], _hidden

# Callback for department-wise cleared exam graph
@app.callback(
    Output("j1-dept-cleared-graph", "figure"),
    Input("j1-zone-dropdown", "value"),
    Input("j1-department-dropdown", "value"),
)
def update_j1_dept_cleared_graph(selected_zone, selected_dept):
    try:
        df = load_fresh_data()
        filtered_df = df.copy()
        
        # Apply filters
        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
        
        # Check for cleared status (J1 uses Status as grade)
        status_col = None
        for col in df.columns:
            if "status" in col.lower() or "result" in col.lower() or "cleared" in col.lower():
                status_col = col
                break
        
        if status_col and "Department" in filtered_df.columns:
            s = filtered_df[status_col].astype(str).str.strip().str.upper()
            cleared_df = filtered_df[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]
            title_suffix = " (Cleared Only)"
        elif "Department" in filtered_df.columns:
            cleared_df = filtered_df
            title_suffix = " (All Records - no status column)"
        else:
            return go.Figure().add_annotation(
                text="No department data found",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        if cleared_df.empty:
            return go.Figure().add_annotation(
                text="No data available for selected filters",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        # Count by department
        dept_counts = cleared_df.groupby("Department").size().reset_index(name="Count")
        dept_counts = dept_counts.sort_values("Count", ascending=True)
        
        dept_labels = dept_counts["Department"].tolist()

        fig = go.Figure(data=[go.Bar(
            y=dept_counts["Department"],
            x=dept_counts["Count"],
            orientation='h',
            marker=dict(color="#3498db"),
            text=dept_counts["Count"],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{y}</b><br>Cleared: %{x}<extra></extra>"
        )])
        
        fig.update_layout(
            title=dict(
                text=f"<b>Department-wise Exam Clearance{title_suffix}</b>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Number of People Cleared",
            yaxis_title="",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=200, r=40, t=60, b=40),
            height=800,
            font=dict(size=13),
            xaxis=dict(
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True
            ),
            yaxis=dict(
                tickfont=dict(size=11),
                tickmode="array",
                tickvals=dept_labels,
                ticktext=dept_labels,
                automargin=True
            )
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )

# Callback to show department details when clicked
@app.callback(
    Output("j1-dept-summary", "children"),
    Output("j1-dept-detail-table", "data"),
    Output("j1-dept-detail-table", "columns"),
    Output("j1-dept-table-wrapper", "style"),
    Input("j1-dept-cleared-graph", "clickData"),
    State("j1-zone-dropdown", "value"),
    State("j1-department-dropdown", "value"),
)
def show_j1_dept_details(clickData, selected_zone, selected_dept):
    _hidden = {"display": "none", "padding": "0 10px"}
    _shown  = {"display": "block", "padding": "0 10px"}
    try:
        df = load_fresh_data()

        if clickData is None:
            placeholder = html.Div([
                html.H5("Department Details", style={"color": "#666", "textAlign": "center", "marginTop": "50px"}),
                html.P("Click on a department in the graph to see details",
                       style={"textAlign": "center", "color": "#999", "fontSize": "14px"})
            ])
            return placeholder, [], [], _hidden

        dept = clickData["points"][0]["y"]
        filtered_df = df.copy()

        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]

        status_col = None
        for col in df.columns:
            if "status" in col.lower() or "result" in col.lower() or "cleared" in col.lower():
                status_col = col
                break

        dept_data = filtered_df[filtered_df["Department"] == dept]
        if status_col:
            s = dept_data[status_col].astype(str).str.strip().str.upper()
            dept_data = dept_data[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]

        if dept_data.empty:
            return html.Div([html.H5(f"No cleared data for {dept}", style={"color": "#666"})]), [], [], _hidden

        grade_col = "Status" if "Status" in df.columns else None
        total_cleared = len(dept_data)
        grade_counts = {}
        if grade_col and grade_col in dept_data.columns:
            grade_counts = dept_data[grade_col].value_counts().to_dict()

        display_columns = []
        for col in ["Name", "Employee ID", "Zone", "Department"]:
            if col in dept_data.columns:
                display_columns.append(col)
        if grade_col:
            display_columns.append(grade_col)
        available_columns = [col for col in display_columns if col in dept_data.columns]

        summary = html.Div([
            html.H4(f"{dept}", style={"color": "#0d6efd", "marginBottom": "15px", "fontSize": "18px"}),
            html.Div([
                html.Div([
                    html.Div("Total Cleared", style={"fontSize": "12px", "color": "#666"}),
                    html.Div(f"{total_cleared}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0d6efd"})
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "10px"}),
                html.Div([
                    html.Div("Grade Breakdown", style={"fontSize": "12px", "color": "#666", "marginBottom": "8px", "fontWeight": "600"}),
                    html.Div([
                        html.Div([
                            html.Span(f"{g}: ", style={"fontSize": "11px", "fontWeight": "600"}),
                            html.Span(f"{c}", style={"fontSize": "11px", "color": "#0d6efd"})
                        ], style={"marginBottom": "4px"}) for g, c in grade_counts.items()
                    ]) if grade_counts else html.P("No grade data available", style={"fontSize": "11px", "color": "#999"})
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "15px"})
            ])
        ])

        return (
            summary,
            dept_data[available_columns].fillna("N/A").to_dict("records"),
            [{"name": col, "id": col} for col in available_columns],
            _shown
        )
    except Exception as e:
        return html.Div([html.P(f"Error: {str(e)}", style={"color": "#e74c3c"})]), [], [], _hidden

# Callback for grade-wise cleared exam graph
@app.callback(
    Output("j1-grade-cleared-graph", "figure"),
    Input("j1-zone-dropdown", "value"),
    Input("j1-department-dropdown", "value"),
)
def update_j1_grade_cleared_graph(selected_zone, selected_dept):
    try:
        df = load_fresh_data()
        filtered_df = df.copy()
        
        # Apply filters
        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]
        
        # In J1, grade buckets are in Status column
        status_col = "Status" if "Status" in df.columns else None
        grade_col = status_col

        if status_col is None:
            return go.Figure().add_annotation(
                text="No Status column found",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        # Filter for cleared exams (PASS/SILVER/BRONZE/GOLD/PLATINUM)
        s = filtered_df[status_col].astype(str).str.strip().str.upper()
        cleared_df = filtered_df[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]
        
        if cleared_df.empty:
            return go.Figure().add_annotation(
                text="No cleared exam data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5, showarrow=False,
                font=dict(size=16, color="#666")
            )
        
        # Count by grade
        grade_counts = cleared_df.groupby(grade_col).size().reset_index(name="Count")
        grade_counts = grade_counts.sort_values("Count", ascending=True)
        
        fig = go.Figure(data=[go.Bar(
            y=grade_counts[grade_col],
            x=grade_counts["Count"],
            orientation='h',
            marker=dict(color="#9b59b6"),
            text=grade_counts["Count"],
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{y}</b><br>Cleared: %{x}<extra></extra>"
        )])
        
        fig.update_layout(
            title=dict(
                text="<b>Grade-wise Exam Clearance</b>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Number of People Cleared",
            yaxis_title="",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=100, r=40, t=60, b=40),
            height=500,
            font=dict(size=13),
            xaxis=dict(
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True
            ),
            yaxis=dict(
                tickfont=dict(size=13)
            )
        )
        
        return fig
    except Exception as e:
        return go.Figure().add_annotation(
            text=f"Error: {str(e)}",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )

# Callback to show grade details when clicked
@app.callback(
    Output("j1-grade-summary", "children"),
    Output("j1-grade-detail-table", "data"),
    Output("j1-grade-detail-table", "columns"),
    Output("j1-grade-table-wrapper", "style"),
    Input("j1-grade-cleared-graph", "clickData"),
    State("j1-zone-dropdown", "value"),
    State("j1-department-dropdown", "value"),
)
def show_j1_grade_details(clickData, selected_zone, selected_dept):
    _hidden = {"display": "none", "padding": "0 10px"}
    _shown  = {"display": "block", "padding": "0 10px"}
    try:
        df = load_fresh_data()

        if clickData is None:
            placeholder = html.Div([
                html.H5("Grade Details", style={"color": "#666", "textAlign": "center", "marginTop": "50px"}),
                html.P("Click on a grade in the graph to see details",
                       style={"textAlign": "center", "color": "#999", "fontSize": "14px"})
            ])
            return placeholder, [], [], _hidden

        grade = clickData["points"][0]["y"]
        filtered_df = df.copy()

        if selected_zone != "All" and "Zone" in df.columns:
            filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
        if selected_dept != "All" and "Department" in df.columns:
            filtered_df = filtered_df[filtered_df["Department"] == selected_dept]

        status_col = "Status" if "Status" in df.columns else None
        grade_col = status_col
        score_col = None
        for col in df.columns:
            if "score" in col.lower():
                score_col = col

        grade_data = filtered_df[filtered_df[grade_col] == grade] if grade_col else pd.DataFrame()
        if status_col and not grade_data.empty:
            s = grade_data[status_col].astype(str).str.strip().str.upper()
            grade_data = grade_data[s.isin(["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"])]

        if grade_data.empty:
            return html.Div([html.H5(f"No cleared data for grade {grade}", style={"color": "#666"})]), [], [], _hidden

        total_cleared = len(grade_data)
        display_columns = []
        for col in ["Name", "Employee ID", "Department", "Zone"]:
            if col in grade_data.columns:
                display_columns.append(col)
        if grade_col:
            display_columns.append(grade_col)
        if score_col:
            display_columns.append(score_col)
        available_columns = [col for col in display_columns if col in grade_data.columns]

        summary = html.Div([
            html.H4(f"Grade: {grade}", style={"color": "#0d6efd", "marginBottom": "15px", "fontSize": "18px"}),
            html.Div([
                html.Div([
                    html.Div("Total Cleared", style={"fontSize": "12px", "color": "#666"}),
                    html.Div(f"{total_cleared}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0d6efd"})
                ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "15px"})
            ])
        ])

        return (
            summary,
            grade_data[available_columns].fillna("N/A").to_dict("records"),
            [{"name": col, "id": col} for col in available_columns],
            _shown
        )
    except Exception as e:
        return html.Div([html.P(f"Error: {str(e)}", style={"color": "#e74c3c"})]), [], [], _hidden

# Callback to check employee status by Employee ID
@app.callback(
    Output("j1-emp-status-output", "children"),
    Input("j1-emp-id-btn", "n_clicks"),
    State("j1-emp-id-input", "value"),
    prevent_initial_call=True
)
def check_j1_emp_status(n_clicks, emp_id):
    if not n_clicks or not emp_id:
        return ""
    
    try:
        df = load_fresh_data()
        
        # Check if Employee ID column exists
        emp_col = None
        for col in df.columns:
            if "employee id" in col.lower() or "emp id" in col.lower():
                emp_col = col
                break
                
        if not emp_col:
            return html.Div("Employee ID column not found in data.", style={"color": "red"})
            
        # Search for employee
        emp_data = df[df[emp_col].astype(str).str.strip().str.lower() == str(emp_id).strip().lower()]
        
        if emp_data.empty:
            return html.Div(f"No record found for Employee ID: {emp_id}", style={"color": "red"})
            
        # Get status
        status_col = None
        for col in df.columns:
            if "status" in col.lower() or "result" in col.lower() or "cleared" in col.lower():
                status_col = col
                break
                
        if not status_col:
            return html.Div(f"Employee found, but status column is missing.", style={"color": "orange"})
            
        status_val = emp_data.iloc[-1][status_col]
        name_val = emp_data.iloc[-1]["Name"] if "Name" in emp_data.columns else ""
        
        # Determine color for status
        status_upper = str(status_val).strip().upper()
        if status_upper in ["PASS", "SILVER", "BRONZE", "GOLD", "PLATINUM"]:
            color = "green"
        elif status_upper == "FAIL":
            color = "red"
        else:
            color = "black"
            
        name_str = f" ({name_val})" if name_val else ""
        
        return html.Div([
            html.Span("Status for Employee ", style={"fontWeight": "bold"}),
            html.Span(f"{emp_id}{name_str}: "),
            html.Span(f"{status_val}", style={"fontWeight": "bold", "color": color, "fontSize": "16px"})
        ])
        
    except Exception as e:
        return html.Div(f"Error checking status: {str(e)}", style={"color": "red"})

