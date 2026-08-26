import os
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import io
import base64
from dash import html, dcc, Input, Output, State, dash_table
from pathlib import Path

from app import app


DATA_DIR = Path("./Data")
REPORTS_BASE = Path("./assets/qmml_reports")
REPORTS_BASE.mkdir(parents=True, exist_ok=True)


def qmml_admin_phase_to_dep_file(phase: str) -> Path:
    if phase == "Phase 1":
        return DATA_DIR / "Dep vs Score.csv"
    if phase == "Phase 2":
        return DATA_DIR / "Dep_vs_Score_phase2.csv"
    if phase == "Phase 3":
        return DATA_DIR / "Dep_vs_Score_phase3.csv"
    return DATA_DIR / "Dep vs Score.csv"


def qmml_admin_phase_to_zone_file(phase: str) -> Path:
    if phase == "Phase 1":
        return DATA_DIR / "Zone vs Score.csv"
    if phase == "Phase 2":
        return DATA_DIR / "Zone_vs_Score_phase2.csv"
    if phase == "Phase 3":
        return DATA_DIR / "Zone_vs_Score_phase3.csv"
    return DATA_DIR / "Zone vs Score.csv"


def qmml_admin_phase_to_schedule_file(phase: str) -> Path:
    # Existing schedule.csv is Phase 2
    if phase == "Phase 1":
        return DATA_DIR / "schedule_phase1.csv"
    if phase == "Phase 2":
        return DATA_DIR / "schedule.csv"
    if phase == "Phase 3":
        return DATA_DIR / "schedule_phase3.csv"
    return DATA_DIR / "schedule.csv"


def qmml_admin_phase_to_reports_dir(phase: str) -> Path:
    folder = REPORTS_BASE / phase.replace(" ", "_").lower()
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def qmml_admin_read_csv_safely(path: Path) -> pd.DataFrame:
    """Read CSV with different encodings and retry logic, return empty df if missing."""
    import time
    
    if not path.exists():
        return pd.DataFrame()
    
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    max_retries = 3
    retry_delay = 0.1  # 100ms
    
    for attempt in range(max_retries):
        for enc in encodings:
            try:
                df = pd.read_csv(path, dtype=str, encoding=enc)
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



def qmml_admin_save_csv_safely(df: pd.DataFrame, path: Path) -> None:
    """Save CSV atomically with proper flushing to disk."""
    import tempfile
    import shutil
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to a temporary file first
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}_tmp_",
        suffix=path.suffix,
        text=False
    )
    
    try:
        # Write the CSV to the temp file
        with os.fdopen(temp_fd, 'w', encoding='utf-8', newline='') as f:
            df.to_csv(f, index=False)
            f.flush()
            os.fsync(f.fileno())
        
        # Atomically replace the original file
        # On Windows, we need to remove the target first if it exists
        if os.name == 'nt' and path.exists():
            path.unlink()
        
        shutil.move(temp_path, str(path))
        
        # Sync the directory to ensure the rename is persisted
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            os.fsync(dir_fd)
            os.close(dir_fd)
        except (AttributeError, OSError):
            # Not all systems support directory fsync
            pass
            
    except Exception as e:
        # Clean up temp file if something went wrong
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        raise e



def qmml_admin_safe_read_dep_departments(path: Path) -> list[str]:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception:
        try:
            df = pd.read_csv(path, encoding="cp1252")
        except Exception:
            return []
    df.columns = df.columns.str.strip()
    if "Department" not in df.columns:
        return []
    return sorted(
        {str(x).strip() for x in df["Department"].dropna().tolist() if str(x).strip()}
    )


PHASE_OPTIONS = [
    {"label": "Phase 1", "value": "Phase 1"},
    {"label": "Phase 2", "value": "Phase 2"},
    {"label": "Phase 3", "value": "Phase 3"},
]


layout = dbc.Container(
    [
        html.H2("QMML – Admin Panel", className="mt-3 mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Phase"),
                        dcc.Dropdown(
                            id="qmml-admin-phase-dropdown",
                            options=PHASE_OPTIONS,
                            value="Phase 1",
                            clearable=False,
                        ),
                    ],
                    md=4,
                ),
            ],
            className="mb-3",
        ),
        html.Hr(),
        # 1️⃣ Data Management – Editable Tables
        html.H4("Data Management – Editable Tables", className="mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Department vs Score"),
                        html.Div(id="qmml-admin-dep-table-container"),
                        dbc.Row([
                            dbc.Col(
                                dbc.Button(
                                    "Save Department vs Score",
                                    id="qmml-admin-save-dep-button",
                                    color="primary",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Clear Data",
                                    id="qmml-admin-clear-dep-button",
                                    color="danger",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dcc.Upload(
                                    dbc.Button("Upload CSV", color="secondary", size="sm", className="mt-2"),
                                    id="qmml-admin-upload-dep",
                                    multiple=False
                                ),
                                width="auto"
                            )
                        ]),
                        html.Div(
                            id="qmml-admin-save-dep-status",
                            className="mt-1",
                            style={"fontSize": "12px"},
                        ),
                        dcc.Store(id="qmml-admin-dep-refresh", data=0),
                    ],
                    md=12,
                    className="mb-5",
                ),
                dbc.Col(
                    [
                        dbc.Label("Zone vs Score"),
                        html.Div(id="qmml-admin-zone-table-container"),
                        dbc.Row([
                            dbc.Col(
                                dbc.Button(
                                    "Save Zone vs Score",
                                    id="qmml-admin-save-zone-button",
                                    color="primary",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Clear Data",
                                    id="qmml-admin-clear-zone-button",
                                    color="danger",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dcc.Upload(
                                    dbc.Button("Upload CSV", color="secondary", size="sm", className="mt-2"),
                                    id="qmml-admin-upload-zone",
                                    multiple=False
                                ),
                                width="auto"
                            )
                        ]),
                        html.Div(
                            id="qmml-admin-save-zone-status",
                            className="mt-1",
                            style={"fontSize": "12px"},
                        ),
                        dcc.Store(id="qmml-admin-zone-refresh", data=0),
                    ],
                    md=12,
                    className="mb-5",
                ),
                dbc.Col(
                    [
                        dbc.Label("Schedule"),
                        html.Div(id="qmml-admin-schedule-table-container"),
                        dbc.Row([
                            dbc.Col(
                                dbc.Button(
                                    "Save Schedule",
                                    id="qmml-admin-save-schedule-button",
                                    color="primary",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dbc.Button(
                                    "Clear Data",
                                    id="qmml-admin-clear-schedule-button",
                                    color="danger",
                                    size="sm",
                                    className="mt-2",
                                ),
                                width="auto"
                            ),
                            dbc.Col(
                                dcc.Upload(
                                    dbc.Button("Upload CSV", color="secondary", size="sm", className="mt-2"),
                                    id="qmml-admin-upload-schedule",
                                    multiple=False
                                ),
                                width="auto"
                            )
                        ]),
                        html.Div(
                            id="qmml-admin-save-schedule-status",
                            className="mt-1",
                            style={"fontSize": "12px"},
                        ),
                        dcc.Store(id="qmml-admin-schedule-refresh", data=0),
                    ],
                    md=12,
                    className="mb-5",
                ),
            ]
        ),
        html.Hr(),
        # 2️⃣ Reports upload
        html.H4("Upload Department Reports", className="mb-3"),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Phase (for report upload)"),
                        dcc.Dropdown(
                            id="qmml-admin-report-phase-dropdown",
                            options=PHASE_OPTIONS,
                            value="Phase 1",
                            clearable=False,
                        ),
                    ],
                    md=4,
                ),
                dbc.Col(
                    [
                        dbc.Label("Department"),
                        dcc.Dropdown(
                            id="qmml-admin-report-department-dropdown",
                            placeholder="Select Department (from Department vs Score)",
                        ),
                    ],
                    md=4,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        dbc.Label("Upload Report (PDF / DOCX etc.)"),
                        dcc.Upload(
                            id="qmml-admin-report-upload",
                            multiple=False,
                            children=html.Div(
                                [
                                    html.I(className="bi bi-cloud-upload fs-3"),
                                    html.Div("Drag and Drop or Click to Upload"),
                                ]
                            ),
                            style={
                                "width": "100%",
                                "height": "140px",
                                "border": "2px dashed #0d6efd",
                                "borderRadius": "12px",
                                "textAlign": "center",
                                "backgroundColor": "#f8f9fa",
                                "cursor": "pointer",
                                "display": "flex",
                                "flexDirection": "column",
                                "alignItems": "center",
                                "justifyContent": "center",
                            },
                        ),
                        html.Div(
                            id="qmml-admin-report-upload-status",
                            className="mt-2",
                            style={"fontSize": "12px"},
                        ),
                    ],
                    md=8,
                )
            ]
        ),
    ],
    fluid=True,
)


# Helper to create editable table
def create_editable_table(table_id, df):
    columns = [{"name": str(col), "id": str(col), "editable": True} for col in df.columns]
    return dash_table.DataTable(
        id=table_id,
        columns=columns,
        data=df.to_dict("records"),
        editable=True,
        row_deletable=True,
        page_size=20,
        filter_action="native",
        sort_action="native",
        style_table={"overflowX": "auto", "maxHeight": "400px", "overflowY": "auto"},
        style_cell={
            "fontSize": 12,
            "textAlign": "left",
            "minWidth": "100px",
            "width": "150px",
            "maxWidth": "300px",
            "whiteSpace": "normal",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold"
        }
    )

# --- Callbacks for Department vs Score ---
@app.callback(
    Output("qmml-admin-dep-table-container", "children"),
    Input("qmml-admin-phase-dropdown", "value"),
    Input("qmml-admin-dep-refresh", "data"),
)
def update_dep_table(phase, refresh):
    path = qmml_admin_phase_to_dep_file(phase)
    df = qmml_admin_read_csv_safely(path)
    if df.empty:
        df = pd.DataFrame(columns=["S N", "Date of Audit", "Department", "Score"])
    return create_editable_table("qmml-admin-dep-table", df)

@app.callback(
    Output("qmml-admin-save-dep-status", "children"),
    Output("qmml-admin-dep-refresh", "data"),
    Output("qmml-admin-upload-dep", "contents"),  # Reset upload component
    Input("qmml-admin-save-dep-button", "n_clicks"),
    Input("qmml-admin-clear-dep-button", "n_clicks"),
    Input("qmml-admin-upload-dep", "contents"),
    State("qmml-admin-dep-table", "data"),
    State("qmml-admin-phase-dropdown", "value"),
    State("qmml-admin-dep-refresh", "data"),
    State("qmml-admin-upload-dep", "filename"),
    prevent_initial_call=True,
)
def handle_dep_actions(save_clicks, clear_clicks, upload_contents, table_data, phase, refresh, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, refresh, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    path = qmml_admin_phase_to_dep_file(phase)
    
    if trigger_id == "qmml-admin-save-dep-button":
        if table_data is None: return "⚠ No data to save", refresh, dash.no_update
        df = pd.DataFrame(table_data).fillna("")
        qmml_admin_save_csv_safely(df, path)
        return f"✅ Saved to {path.name}", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-clear-dep-button":
        df = pd.DataFrame(columns=["S N", "Date of Audit", "Department", "Score"])
        qmml_admin_save_csv_safely(df, path)
        return "✅ Data cleared", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-upload-dep":
        if upload_contents:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            # Try multiple encodings for the uploaded file
            df = pd.DataFrame()
            for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
                try:
                    df = pd.read_csv(io.StringIO(decoded.decode(enc)))
                    df.columns = df.columns.str.strip()
                    break
                except:
                    continue
            if not df.empty:
                qmml_admin_save_csv_safely(df, path)
                return f"✅ Uploaded {filename}", refresh + 1, None  # Reset upload component
            else:
                return "❌ Failed to read CSV. Check format/encoding.", refresh, dash.no_update
            
    return dash.no_update, refresh, dash.no_update

# --- Callbacks for Zone vs Score ---
@app.callback(
    Output("qmml-admin-zone-table-container", "children"),
    Input("qmml-admin-phase-dropdown", "value"),
    Input("qmml-admin-zone-refresh", "data"),
)
def update_zone_table(phase, refresh):
    path = qmml_admin_phase_to_zone_file(phase)
    df = qmml_admin_read_csv_safely(path)
    if df.empty:
        df = pd.DataFrame(columns=["S N", "Department", "Score", "Zone", "Avg Score"])
    return create_editable_table("qmml-admin-zone-table", df)

@app.callback(
    Output("qmml-admin-save-zone-status", "children"),
    Output("qmml-admin-zone-refresh", "data"),
    Output("qmml-admin-upload-zone", "contents"),  # Reset upload component
    Input("qmml-admin-save-zone-button", "n_clicks"),
    Input("qmml-admin-clear-zone-button", "n_clicks"),
    Input("qmml-admin-upload-zone", "contents"),
    State("qmml-admin-zone-table", "data"),
    State("qmml-admin-phase-dropdown", "value"),
    State("qmml-admin-zone-refresh", "data"),
    State("qmml-admin-upload-zone", "filename"),
    prevent_initial_call=True,
)
def handle_zone_actions(save_clicks, clear_clicks, upload_contents, table_data, phase, refresh, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, refresh, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    path = qmml_admin_phase_to_zone_file(phase)
    
    if trigger_id == "qmml-admin-save-zone-button":
        if table_data is None: return "⚠ No data to save", refresh, dash.no_update
        df = pd.DataFrame(table_data).fillna("")
        qmml_admin_save_csv_safely(df, path)
        return f"✅ Saved to {path.name}", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-clear-zone-button":
        df = pd.DataFrame(columns=["S N", "Department", "Score", "Zone", "Avg Score"])
        qmml_admin_save_csv_safely(df, path)
        return "✅ Data cleared", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-upload-zone":
        if upload_contents:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.DataFrame()
            for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
                try:
                    df = pd.read_csv(io.StringIO(decoded.decode(enc)))
                    df.columns = df.columns.str.strip()
                    break
                except:
                    continue
            if not df.empty:
                qmml_admin_save_csv_safely(df, path)
                return f"✅ Uploaded {filename}", refresh + 1, None  # Reset upload component
            else:
                return "❌ Failed to read CSV. Check format/encoding.", refresh, dash.no_update
            
    return dash.no_update, refresh, dash.no_update


# --- Callbacks for Schedule ---
@app.callback(
    Output("qmml-admin-schedule-table-container", "children"),
    Input("qmml-admin-phase-dropdown", "value"),
    Input("qmml-admin-schedule-refresh", "data"),
)
def update_schedule_table(phase, refresh):
    path = qmml_admin_phase_to_schedule_file(phase)
    df = qmml_admin_read_csv_safely(path)
    if df.empty:
        df = pd.DataFrame(columns=["S N", "Date of audit", "1st half", "2nd half"])
    return create_editable_table("qmml-admin-schedule-table", df)

@app.callback(
    Output("qmml-admin-save-schedule-status", "children"),
    Output("qmml-admin-schedule-refresh", "data"),
    Output("qmml-admin-upload-schedule", "contents"),  # Reset upload component
    Input("qmml-admin-save-schedule-button", "n_clicks"),
    Input("qmml-admin-clear-schedule-button", "n_clicks"),
    Input("qmml-admin-upload-schedule", "contents"),
    State("qmml-admin-schedule-table", "data"),
    State("qmml-admin-phase-dropdown", "value"),
    State("qmml-admin-schedule-refresh", "data"),
    State("qmml-admin-upload-schedule", "filename"),
    prevent_initial_call=True,
)
def handle_schedule_actions(save_clicks, clear_clicks, upload_contents, table_data, phase, refresh, filename):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, refresh, dash.no_update
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    path = qmml_admin_phase_to_schedule_file(phase)
    
    if trigger_id == "qmml-admin-save-schedule-button":
        if table_data is None: return "⚠ No data to save", refresh, dash.no_update
        df = pd.DataFrame(table_data).fillna("")
        qmml_admin_save_csv_safely(df, path)
        return f"✅ Saved to {path.name}", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-clear-schedule-button":
        df = pd.DataFrame(columns=["S N", "Date of audit", "1st half", "2nd half"])
        qmml_admin_save_csv_safely(df, path)
        return "✅ Data cleared", refresh + 1, dash.no_update
        
    elif trigger_id == "qmml-admin-upload-schedule":
        if upload_contents:
            content_type, content_string = upload_contents.split(',')
            decoded = base64.b64decode(content_string)
            df = pd.DataFrame()
            for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
                try:
                    # Specific to schedule: it might have that extra title line if they upload the existing file
                    # So we try to detect and skip if S N is not in header
                    df = pd.read_csv(io.StringIO(decoded.decode(enc)))
                    if "S N" not in df.columns and len(df.columns) > 0 and "S N" in df.iloc[0].values:
                         df = pd.read_csv(io.StringIO(decoded.decode(enc)), header=1)
                    df.columns = df.columns.astype(str).str.strip()
                    break
                except:
                    continue
            if not df.empty:
                qmml_admin_save_csv_safely(df, path)
                return f"✅ Uploaded {filename}", refresh + 1, None  # Reset upload component
            else:
                return "❌ Failed to read CSV. Check format/encoding.", refresh, dash.no_update
            
    return dash.no_update, refresh, dash.no_update


@app.callback(
    Output("qmml-admin-report-department-dropdown", "options"),
    Input("qmml-admin-report-phase-dropdown", "value"),
)
def qmml_admin_update_department_options_for_reports(selected_phase):
    dep_path = qmml_admin_phase_to_dep_file(selected_phase)
    departments = qmml_admin_safe_read_dep_departments(dep_path)
    return [{"label": d, "value": d} for d in departments]


@app.callback(
    Output("qmml-admin-report-upload-status", "children"),
    Input("qmml-admin-report-upload", "contents"),
    State("qmml-admin-report-upload", "filename"),
    State("qmml-admin-report-phase-dropdown", "value"),
    State("qmml-admin-report-department-dropdown", "value"),
    prevent_initial_call=True,
)
def qmml_admin_save_department_report_callback(
    contents, filename, selected_phase, selected_department
):
    if not contents or not filename:
        return "⚠ Please select a file to upload."
    if not selected_phase or not selected_department:
        return "⚠ Please select phase and department before uploading."

    content_type, content_string = contents.split(",", 1)
    import base64

    try:
        decoded = base64.b64decode(content_string)
    except Exception as e:
        return f"❌ Failed to decode uploaded file: {str(e)}"

    safe_dept = selected_department.replace("/", "-").replace("\\", "-").strip()
    extension = os.path.splitext(filename)[1] or ".pdf"
    folder = qmml_admin_phase_to_reports_dir(selected_phase)
    save_path = folder / f"{safe_dept}{extension}"

    try:
        with open(save_path, "wb") as f:
            f.write(decoded)
            f.flush()
            os.fsync(f.fileno())
    except Exception as e:
        return f"❌ Failed to save file: {str(e)}"

    return f"✅ Report saved for {selected_phase} – {safe_dept} ({save_path.name})"

