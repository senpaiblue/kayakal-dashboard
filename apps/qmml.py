import os
from pathlib import Path

import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import html, dcc, Input, Output

from app import app


DATA_DIR = Path("./Data")
REPORTS_BASE = Path("./assets/qmml_reports")


def _safe_read_csv(path: Path) -> pd.DataFrame:
    """Read CSV with multiple encodings and retry logic, return empty df if missing."""
    import time
    
    if not path.exists():
        return pd.DataFrame()

    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(max_retries):
        for enc in encodings:
            try:
                df = pd.read_csv(path, encoding=enc)
                df.columns = df.columns.str.strip()
                return df
            except pd.errors.EmptyDataError:
                # File is empty, return empty DataFrame immediately
                return pd.DataFrame()
            except UnicodeDecodeError:
                # Try next encoding
                continue
            except Exception as e:
                # If it's a file access error and we have retries left, wait and retry
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))  # Exponential backoff
                    break
                continue
    
    return pd.DataFrame()




def _safe_read_schedule_csv(path: Path) -> pd.DataFrame:
    """Read schedule CSV with multiple encodings, handling extra title row."""
    if not path.exists():
        return pd.DataFrame()

    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            # Try reading normally first
            df = pd.read_csv(path, encoding=enc)
            # Check if "S N" is in the header, if not check if it's in the first row
            if "S N" not in df.columns and len(df.columns) > 0:
                # Check if first row contains "S N" - indicates header is on row 2
                if "S N" in df.iloc[0].values:
                    df = pd.read_csv(path, encoding=enc, header=1)
            df.columns = df.columns.astype(str).str.strip()
            return df
        except (UnicodeDecodeError, Exception):
            continue
    return pd.DataFrame()


def _dep_file_for_phase(phase: str) -> Path:
    if phase == "Phase 1":
        return DATA_DIR / "Dep vs Score.csv"
    elif phase == "Phase 2":
        return DATA_DIR / "Dep_vs_Score_phase2.csv"
    elif phase == "Phase 3":
        return DATA_DIR / "Dep_vs_Score_phase3.csv"
    return DATA_DIR / "Dep vs Score.csv"


def _zone_file_for_phase(phase: str) -> Path:
    if phase == "Phase 1":
        return DATA_DIR / "Zone vs Score.csv"
    elif phase == "Phase 2":
        return DATA_DIR / "Zone_vs_Score_phase2.csv"
    elif phase == "Phase 3":
        return DATA_DIR / "Zone_vs_Score_phase3.csv"
    return DATA_DIR / "Zone vs Score.csv"


def _schedule_file_for_phase(phase: str) -> Path:
    # As per requirement: existing schedule.csv is for Phase 2
    if phase == "Phase 1":
        return DATA_DIR / "schedule_phase1.csv"
    elif phase == "Phase 2":
        return DATA_DIR / "schedule.csv"
    elif phase == "Phase 3":
        return DATA_DIR / "schedule_phase3.csv"
    return DATA_DIR / "schedule.csv"


def _reports_dir_for_phase(phase: str) -> Path:
    folder = REPORTS_BASE / phase.replace(" ", "_").lower()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


PHASE_OPTIONS = [
    {"label": "Phase 1", "value": "Phase 1"},
    {"label": "Phase 2", "value": "Phase 2"},
    {"label": "Phase 3", "value": "Phase 3"},
]


layout = dbc.Container(
    [
        html.H2("QMML Dashboard", style={"marginBottom": "20px", "color": "#0d6efd"}),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label(
                            "Select Phase",
                            style={
                                "fontWeight": "600",
                                "fontSize": "14px",
                                "marginBottom": "8px",
                                "display": "block",
                            },
                        ),
                        dcc.Dropdown(
                            id="qmml-phase-dropdown",
                            options=PHASE_OPTIONS,
                            value="Phase 1",
                            clearable=False,
                        ),
                    ],
                    width=4,
                ),
            ],
            style={"marginBottom": "20px"},
        ),
        html.Hr(),
        # 1️⃣ Department vs Score
        html.H4(
            "Department vs Score",
            style={"marginBottom": "15px", "color": "#333"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="qmml-dep-score-graph", style={"height": "480px"}),
                    width=7,
                ),
                dbc.Col(
                    html.Div(id="qmml-dep-detail-panel", style={"padding": "10px"}),
                    width=5,
                ),
            ],
            style={"marginBottom": "30px"},
        ),
        html.Hr(),
        # 2️⃣ Zone vs Score
        html.H4("Zone vs Score", style={"marginBottom": "15px", "color": "#333"}),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="qmml-zone-score-graph", style={"height": "480px"}),
                    width=7,
                ),
                dbc.Col(
                    html.Div(id="qmml-zone-detail-panel", style={"padding": "10px"}),
                    width=5,
                ),
            ],
            style={"marginBottom": "30px"},
        ),
        html.Hr(),
        # 3️⃣ Schedule chart
        html.H4(
            "Assessment Schedule",
            style={"marginBottom": "15px", "color": "#333"},
        ),
        dbc.Row(
            [
                dbc.Col(
                    dcc.Graph(id="qmml-schedule-chart", style={"height": "700px"}),
                    width=12,
                ),
            ],
            style={"marginBottom": "50px"},
        ),
        html.Hr(),
        # 4️⃣ Reports download
        html.H4(
            "Department-wise Reports",
            style={"marginBottom": "15px", "color": "#333"},
        ),
        html.Div(id="qmml-report-downloads"),
        # Interval for real-time synchronization
        dcc.Interval(
            id="qmml-interval-sync",
            interval=5 * 1000,  # 5 seconds
            n_intervals=0,
        ),
    ],
    fluid=True,
    style={"padding": "20px", "fontFamily": "Arial"},
)


@app.callback(
    Output("qmml-dep-score-graph", "figure"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_update_department_score_graph(selected_phase, n_intervals):
    df_dep = _safe_read_csv(_dep_file_for_phase(selected_phase))

    if df_dep.empty or "Department" not in df_dep.columns or "Score" not in df_dep.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Department vs Score data not available for this phase.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666"),
        )
        return fig

    df_plot = df_dep.copy()
    df_plot["Score"] = pd.to_numeric(df_plot["Score"], errors="coerce")
    df_plot = df_plot.dropna(subset=["Score"])
    df_plot = df_plot.sort_values("Score", ascending=True)

    fig = px.bar(
        df_plot,
        x="Score",
        y="Department",
        orientation="h",
        text="Score",
    )
    fig.update_traces(
        marker_color="#0d6efd",
        texttemplate="%{text:.2f}",
        textposition="outside",
    )
    fig.update_layout(
        title=dict(
            text=f"<b>Department vs Score – {selected_phase}</b>",
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Score",
        yaxis_title="Department",
        margin=dict(l=200, r=40, t=60, b=40),
        plot_bgcolor="rgba(240,240,240,0.3)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=480,
    )
    return fig


@app.callback(
    Output("qmml-dep-detail-panel", "children"),
    Input("qmml-dep-score-graph", "clickData"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_show_department_details(click_data, selected_phase, n_intervals):
    # Check which input triggered this callback
    ctx = dash.callback_context
    if not ctx.triggered:
        trigger_id = None
    else:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Only show empty state if there's no click data AND the trigger was the graph click (not interval)
    if click_data is None and trigger_id != "qmml-interval-sync":
        return html.Div(
            [
                html.H5(
                    "Department Trend",
                    style={"color": "#666", "textAlign": "center", "marginTop": "50px"},
                ),
                html.P(
                    "Click on a department bar to view trends across all phases.",
                    style={"textAlign": "center", "color": "#999", "fontSize": "14px"},
                ),
            ]
        )
    
    # If interval triggered but no click data, return no update to preserve current state
    if click_data is None:
        return dash.no_update


    department = click_data["points"][0]["y"]
    
    # Collect data from all three phases
    trend_data = []
    for phase in ["Phase 1", "Phase 2", "Phase 3"]:
        df_phase = _safe_read_csv(_dep_file_for_phase(phase))
        if not df_phase.empty and "Department" in df_phase.columns and "Score" in df_phase.columns:
            df_phase["Score"] = pd.to_numeric(df_phase["Score"], errors="coerce")
            # Case-insensitive and whitespace-tolerant matching
            df_phase["Department_normalized"] = df_phase["Department"].astype(str).str.strip().str.lower()
            department_normalized = str(department).strip().lower()
            dep_rows = df_phase[df_phase["Department_normalized"] == department_normalized]
            if not dep_rows.empty:
                latest_row = dep_rows.iloc[-1]
                score = latest_row.get("Score")
                if pd.notna(score):
                    trend_data.append({
                        "Phase": phase,
                        "Score": float(score)
                    })
    
    if not trend_data:
        return html.Div(
            f"No trend data available for {department}.",
            style={"color": "#666", "textAlign": "center", "marginTop": "50px"},
        )
    
    df_trend = pd.DataFrame(trend_data)
    
    # Create trend line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_trend["Phase"],
        y=df_trend["Score"],
        mode='lines+markers+text',
        name=department,
        line=dict(color='#0d6efd', width=3),
        marker=dict(size=12, color='#0d6efd'),
        text=df_trend["Score"].round(2),
        textposition="top center",
        textfont=dict(size=12, color='#0d6efd', family='Arial Black'),
        hovertemplate="<b>%{x}</b><br>Score: %{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>{department}</b><br><sub>Performance Trend Across Phases</sub>",
            x=0.5,
            xanchor="center",
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Phase",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.3)'
        ),
        yaxis=dict(
            title="Score",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.3)',
            range=[0, max(df_trend["Score"]) * 1.2] if len(df_trend) > 0 else [0, 5]
        ),
        plot_bgcolor="rgba(240,240,240,0.2)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=60, r=40, t=80, b=60),
        hovermode="x unified",
        showlegend=False
    )
    
    trend_chart = dcc.Graph(figure=fig, config={'displayModeBar': False})
    
    # Check for reports across all phases
    safe_dept = department.replace("/", "-").replace("\\", "-").strip()
    safe_dept_lower = safe_dept.lower()
    reports_section = []
    
    for phase in ["Phase 1", "Phase 2", "Phase 3"]:
        phase_dir = REPORTS_BASE / phase.replace(" ", "_").lower()
        if phase_dir.exists():
            for file in phase_dir.iterdir():
                if file.is_file() and file.suffix.lower() in [".pdf", ".xlsx", ".xls", ".doc", ".docx"]:
                    # Extract department name from filename
                    file_stem = file.stem
                    dept_name = file_stem.split(".")[0] if "." in file_stem else file_stem
                    
                    # Case-insensitive matching
                    if dept_name.lower() == safe_dept_lower:
                        href = f"/assets/qmml_reports/{phase.replace(' ', '_').lower()}/{file.name}"
                        reports_section.append(
                            dbc.Card(
                                dbc.CardBody(
                                    dbc.Row(
                                        [
                                            dbc.Col(
                                                [
                                                    html.Div(
                                                        [
                                                            html.I(className="bi bi-file-earmark-text me-2", style={"color": "#0d6efd"}),
                                                            html.Strong(phase, style={"color": "#0d6efd", "fontSize": "12px"}),
                                                        ],
                                                        style={"marginBottom": "3px"}
                                                    ),
                                                    html.Div(
                                                        file.name,
                                                        style={"fontSize": "11px", "color": "#666"}
                                                    ),
                                                ],
                                                md=7,
                                            ),
                                            dbc.Col(
                                                html.A(
                                                    [html.I(className="bi bi-download me-1"), "Download"],
                                                    href=href,
                                                    target="_blank",
                                                    className="btn btn-sm btn-outline-primary",
                                                    style={"fontSize": "11px"}
                                                ),
                                                md=5,
                                                className="text-end",
                                            ),
                                        ],
                                        align="center",
                                    )
                                ),
                                className="mb-2",
                                style={"border": "1px solid #dee2e6"}
                            )
                        )
    
    # Build the content to return
    content = [trend_chart]
    
    if reports_section:
        content.append(html.Hr(style={"margin": "20px 0"}))
        content.append(
            html.Div([
                html.H6(
                    "Available Reports",
                    style={"marginBottom": "10px", "color": "#333", "fontWeight": "600"}
                ),
                html.Div(reports_section)
            ])
        )
    
    return html.Div(content)


@app.callback(
    Output("qmml-zone-score-graph", "figure"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_update_zone_score_graph(selected_phase, n_intervals):
    df_zone = _safe_read_csv(_zone_file_for_phase(selected_phase))

    if df_zone.empty or "Zone" not in df_zone.columns:
        fig = go.Figure()
        fig.add_annotation(
            text="Zone vs Score data not available for this phase.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666"),
        )
        return fig

    df_zone["Avg Score"] = pd.to_numeric(df_zone.get("Avg Score"), errors="coerce")
    df_zone = df_zone.dropna(subset=["Zone"])

    zone_summary = (
        df_zone.groupby("Zone")["Avg Score"]
        .mean()
        .reset_index()
        .sort_values("Avg Score", ascending=True)
    )

    fig = px.bar(
        zone_summary,
        x="Avg Score",
        y="Zone",
        orientation="h",
        text="Avg Score",
    )
    fig.update_traces(
        marker_color="#27ae60",
        texttemplate="%{text:.2f}",
        textposition="outside",
    )
    fig.update_layout(
        title=dict(
            text=f"<b>Zone vs Average Score – {selected_phase}</b>",
            x=0.5,
            xanchor="center",
        ),
        xaxis_title="Average Score",
        yaxis_title="Zone",
        margin=dict(l=200, r=40, t=60, b=40),
        plot_bgcolor="rgba(240,240,240,0.3)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=480,
    )
    return fig


@app.callback(
    Output("qmml-zone-detail-panel", "children"),
    Input("qmml-zone-score-graph", "clickData"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_show_zone_details(click_data, selected_phase, n_intervals):
    # Check which input triggered this callback
    ctx = dash.callback_context
    if not ctx.triggered:
        trigger_id = None
    else:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    
    # Only show empty state if there's no click data AND the trigger was the graph click (not interval)
    if click_data is None and trigger_id != "qmml-interval-sync":
        return html.Div(
            [
                html.H5(
                    "Zone Trend",
                    style={"color": "#666", "textAlign": "center", "marginTop": "50px"},
                ),
                html.P(
                    "Click on a zone bar to view trends across all phases.",
                    style={"textAlign": "center", "color": "#999", "fontSize": "14px"},
                ),
            ]
        )
    
    # If interval triggered but no click data, return no update to preserve current state
    if click_data is None:
        return dash.no_update


    zone_clicked = click_data["points"][0]["y"]
    
    # Collect data from all three phases
    trend_data = []
    for phase in ["Phase 1", "Phase 2", "Phase 3"]:
        df_phase = _safe_read_csv(_zone_file_for_phase(phase))
        if not df_phase.empty and "Zone" in df_phase.columns:
            df_phase["Avg Score"] = pd.to_numeric(df_phase.get("Avg Score"), errors="coerce")
            zone_rows = df_phase[df_phase["Zone"] == zone_clicked]
            if not zone_rows.empty:
                avg_score = zone_rows["Avg Score"].mean()
                if pd.notna(avg_score):
                    trend_data.append({
                        "Phase": phase,
                        "Avg Score": float(avg_score)
                    })
    
    if not trend_data:
        return html.Div(
            f"No trend data available for {zone_clicked}.",
            style={"color": "#666", "textAlign": "center", "marginTop": "50px"},
        )
    
    df_trend = pd.DataFrame(trend_data)
    
    # Create trend line chart
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=df_trend["Phase"],
        y=df_trend["Avg Score"],
        mode='lines+markers+text',
        name=zone_clicked,
        line=dict(color='#27ae60', width=3),
        marker=dict(size=12, color='#27ae60'),
        text=df_trend["Avg Score"].round(2),
        textposition="top center",
        textfont=dict(size=12, color='#27ae60', family='Arial Black'),
        hovertemplate="<b>%{x}</b><br>Avg Score: %{y:.2f}<extra></extra>"
    ))
    
    fig.update_layout(
        title=dict(
            text=f"<b>{zone_clicked}</b><br><sub>Average Score Trend Across Phases</sub>",
            x=0.5,
            xanchor="center",
            font=dict(size=16)
        ),
        xaxis=dict(
            title="Phase",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.3)'
        ),
        yaxis=dict(
            title="Average Score",
            showgrid=True,
            gridcolor='rgba(200,200,200,0.3)',
            range=[0, max(df_trend["Avg Score"]) * 1.2] if len(df_trend) > 0 else [0, 5]
        ),
        plot_bgcolor="rgba(240,240,240,0.2)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=400,
        margin=dict(l=60, r=40, t=80, b=60),
        hovermode="x unified",
        showlegend=False
    )
    
    return dcc.Graph(figure=fig, config={'displayModeBar': False})


@app.callback(
    Output("qmml-schedule-chart", "figure"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_update_schedule_chart(selected_phase, n_intervals):
    df_sch = _safe_read_schedule_csv(_schedule_file_for_phase(selected_phase))

    if df_sch.empty:
        fig = go.Figure()
        fig.add_annotation(
            text="Schedule data not available for this phase.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666"),
        )
        return fig

    # Expect columns: "S N", "Date of audit", "1st half", "2nd half"
    date_col = None
    for col in df_sch.columns:
        if "date" in col.lower():
            date_col = col
            break

    if not date_col:
        fig = go.Figure()
        fig.add_annotation(
            text="Could not identify date column in schedule.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666"),
        )
        return fig

    # Create a better structured dataframe for Gantt chart
    schedule_data = []
    
    for _, row in df_sch.iterrows():
        date_str = row.get(date_col)
        first_half = row.get("1st half", "")
        second_half = row.get("2nd half", "")
        
        if pd.isna(date_str):
            continue
            
        try:
            base_date = pd.to_datetime(date_str, errors="coerce")
            if pd.isna(base_date):
                continue
                
            # First half: 9 AM to 1 PM
            if first_half and str(first_half).strip():
                schedule_data.append({
                    "Department": str(first_half).strip(),
                    "Start": base_date + pd.Timedelta(hours=9),
                    "End": base_date + pd.Timedelta(hours=13),
                    "Slot": "1st Half (9 AM - 1 PM)",
                    "Date": base_date.strftime("%d/%m/%Y")
                })
            
            # Second half: 2 PM to 6 PM
            if second_half and str(second_half).strip():
                schedule_data.append({
                    "Department": str(second_half).strip(),
                    "Start": base_date + pd.Timedelta(hours=14),
                    "End": base_date + pd.Timedelta(hours=18),
                    "Slot": "2nd Half (2 PM - 6 PM)",
                    "Date": base_date.strftime("%d/%m/%Y")
                })
        except Exception:
            continue

    if not schedule_data:
        fig = go.Figure()
        fig.add_annotation(
            text="No valid schedule rows to display.",
            xref="paper",
            yref="paper",
            x=0.5,
            y=0.5,
            showarrow=False,
            font=dict(size=16, color="#666"),
        )
        return fig

    df_gantt = pd.DataFrame(schedule_data)
    
    # Create Gantt chart
    fig = px.timeline(
        df_gantt,
        x_start="Start",
        x_end="End",
        y="Department",
        color="Slot",
        hover_data=["Date", "Department", "Slot"],
        color_discrete_map={
            "1st Half (9 AM - 1 PM)": "#0d6efd",
            "2nd Half (2 PM - 6 PM)": "#dc3545"
        }
    )
    
    # Improve layout
    fig.update_yaxes(
        categoryorder="total ascending",
        title="Department"
    )
    
    fig.update_xaxes(
        title="Schedule Timeline",
        tickformat="%d %b\n%Y"
    )
    
    fig.update_layout(
        title=dict(
            text=f"<b>QMML Assessment Schedule – {selected_phase}</b>",
            x=0.5,
            xanchor="center",
            font=dict(size=18)
        ),
        margin=dict(l=250, r=40, t=80, b=80),
        plot_bgcolor="rgba(240,240,240,0.3)",
        paper_bgcolor="rgba(0,0,0,0)",
        height=650,
        legend=dict(
            title="Audit Slot",
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        hovermode="closest"
    )
    
    # Update hover template for better readability
    fig.update_traces(
        hovertemplate="<b>%{y}</b><br>" +
                      "Date: %{customdata[0]}<br>" +
                      "Slot: %{fullData.name}<br>" +
                      "<extra></extra>"
    )
    
    return fig


@app.callback(
    Output("qmml-report-downloads", "children"),
    Input("qmml-phase-dropdown", "value"),
    Input("qmml-interval-sync", "n_intervals"),
)
def qmml_display_phase_reports_list(selected_phase, n_intervals):
    """Display all department reports for the selected phase in the bottom section."""
    folder = _reports_dir_for_phase(selected_phase)

    files = []
    if folder.exists():
        for fname in sorted(os.listdir(folder)):
            full_path = folder / fname
            if not full_path.is_file():
                continue
            dept_name = os.path.splitext(fname)[0]
            rel_path = str(full_path).replace("\\", "/").split("assets/")[-1]
            href = f"/assets/{rel_path}"

            files.append(
                dbc.Card(
                    dbc.CardBody(
                        dbc.Row(
                            [
                                dbc.Col(
                                    html.Div(
                                        [
                                            html.I(className="bi bi-file-earmark-text me-2", style={"color": "#0d6efd"}),
                                            html.Span(
                                                dept_name,
                                                style={
                                                    "fontWeight": "600",
                                                    "fontSize": "14px",
                                                }
                                            )
                                        ],
                                        style={"display": "flex", "alignItems": "center"}
                                    ),
                                    md=8,
                                ),
                                dbc.Col(
                                    html.A(
                                        [html.I(className="bi bi-download me-1"), "Download"],
                                        href=href,
                                        target="_blank",
                                        className="btn btn-primary btn-sm",
                                    ),
                                    md=4,
                                    className="text-end",
                                ),
                            ],
                            align="center",
                        )
                    ),
                    className="mb-2",
                    style={"boxShadow": "0 1px 3px rgba(0,0,0,0.1)"}
                )
            )

    if not files:
        return dbc.Alert(
            [
                html.I(className="bi bi-info-circle me-2"),
                f"No reports uploaded for {selected_phase} yet."
            ],
            color="light",
            className="d-flex align-items-center",
            style={"fontSize": "14px"}
        )

    return html.Div(files)

