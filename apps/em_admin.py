import os
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import io
import base64
from dash import html, dcc, Input, Output, State, dash_table
from pathlib import Path
from datetime import datetime

from app import app

DATA_DIR = Path("./Data")
DATA_DIR.mkdir(parents=True, exist_ok=True)


def em_admin_read_csv_safely(path: Path) -> pd.DataFrame:
    """Read CSV with header detection and column filtering, matching em.py logic."""
    import time
    
    if not path.exists():
        return pd.DataFrame()
    
    try:
        # Find the header row dynamically (same as em.py)
        for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin1']:
            try:
                # Read raw to find header
                raw_df = pd.read_csv(path, encoding=enc, header=None, dtype=str)
                header_idx = -1
                for i, row in raw_df.iterrows():
                    if row.astype(str).str.contains('Department', case=False).any():
                        header_idx = i
                        break
                
                if header_idx != -1:
                    # Re-read from that row
                    df = pd.read_csv(path, skiprows=header_idx, encoding=enc)
                    break
                else:
                    # Fallback to simple read
                    df = pd.read_csv(path, encoding=enc, dtype=str)
                    break
            except:
                continue
        else:
            return pd.DataFrame()
    except Exception as e:
        return pd.DataFrame()
    
    # Clean column names
    df.columns = df.columns.astype(str).str.strip()
    
    # Keep only required columns (drop Unnamed columns)
    required_cols = ['Department', 'Source', 'Date', 'Daily Count', 'Total Violations']
    cols_to_keep = [col for col in df.columns if col in required_cols or col == 'Image']
    if cols_to_keep:
        df = df[cols_to_keep]
    
    return df


def em_admin_save_csv_safely(df: pd.DataFrame, path: Path) -> None:
    """Save CSV atomically with proper flushing to disk."""
    import tempfile
    import shutil
    
    path.parent.mkdir(parents=True, exist_ok=True)
    
    temp_fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.stem}_tmp_",
        suffix=path.suffix,
        text=False
    )
    
    try:
        with os.fdopen(temp_fd, 'w', encoding='utf-8', newline='') as f:
            df.to_csv(f, index=False)
            f.flush()
            os.fsync(f.fileno())
        
        if os.name == 'nt' and path.exists():
            path.unlink()
        
        shutil.move(temp_path, str(path))
        
        try:
            dir_fd = os.open(str(path.parent), os.O_RDONLY)
            os.fsync(dir_fd)
            os.close(dir_fd)
        except (AttributeError, OSError):
            pass
            
    except Exception as e:
        try:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
        except:
            pass
        raise e


layout = dbc.Container([
    html.H2("Emission Control – Admin Panel", className="mt-3 mb-3"),
    
    html.Hr(),
    
    # Upload Section
    html.H4("Upload Emission Report CSV", className="mb-3"),
    
    dbc.Row([
        dbc.Col([
            dbc.Label("Upload Emission Report CSV"),
            dcc.Upload(
                id="em-admin-upload-csv",
                multiple=False,
                children=html.Div([
                    html.I(className="bi bi-cloud-upload fs-3"),
                    html.Div("Drag and Drop or Click to Upload CSV"),
                ]),
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
                id="em-admin-upload-status",
                className="mt-2",
                style={"fontSize": "12px"},
            ),
        ], md=8),
    ], className="mb-4"),
    
    # Date Range Section
    html.H4("Date Range Selection", className="mb-3"),
    dbc.Row([
        dbc.Col([
            dbc.Label("From Date"),
            dcc.DatePickerSingle(
                id="em-admin-date-start",
                placeholder="Select start date",
                display_format="DD-MMM-YYYY",
                className="mb-2"
            ),
        ], md=3),
        dbc.Col([
            dbc.Label("To Date"),
            dcc.DatePickerSingle(
                id="em-admin-date-end",
                placeholder="Select end date",
                display_format="DD-MMM-YYYY",
                className="mb-2"
            ),
        ], md=3),
        dbc.Col([
            dbc.Label("Apply Filter"),
            html.Br(),
            dbc.Button(
                "Apply Date Range",
                id="em-admin-apply-dates",
                color="primary",
                size="sm",
            ),
        ], md=3),
    ], className="mb-4"),
    
    html.Hr(),
    
    # Data Table Section
    html.H4("Uploaded Data Preview", className="mb-3"),
    html.Div(id="em-admin-data-table-container"),
    
    dbc.Row([
        dbc.Col(
            dbc.Button(
                "Save Data",
                id="em-admin-save-button",
                color="success",
                size="sm",
                className="mt-2",
            ),
            width="auto"
        ),
        dbc.Col(
            dbc.Button(
                "Clear All Data",
                id="em-admin-clear-button",
                color="danger",
                size="sm",
                className="mt-2",
            ),
            width="auto"
        ),
    ]),
    
    html.Div(
        id="em-admin-save-status",
        className="mt-2",
        style={"fontSize": "12px"},
    ),
    
    # Store for data refresh
    dcc.Store(id="em-admin-data-refresh", data=0),
    
], fluid=True)


def em_admin_create_editable_table(df):
    """Create editable DataTable from DataFrame."""
    if df.empty:
        return html.P("No data uploaded yet", className="text-muted")
    
    columns = [{"name": str(col), "id": str(col), "editable": True} for col in df.columns]
    
    return dash_table.DataTable(
        id="em-admin-data-table",
        columns=columns,
        data=df.to_dict("records"),
        editable=True,
        row_deletable=True,
        page_size=20,
        filter_action="native",
        sort_action="native",
        style_table={"overflowX": "auto", "maxHeight": "500px", "overflowY": "auto"},
        style_cell={
            "fontSize": 11,
            "textAlign": "left",
            "minWidth": "80px",
            "width": "120px",
            "maxWidth": "250px",
            "whiteSpace": "normal",
        },
        style_header={
            "backgroundColor": "rgb(230, 230, 230)",
            "fontWeight": "bold"
        }
    )


@app.callback(
    Output("em-admin-data-table-container", "children"),
    Input("em-admin-data-refresh", "data"),
)
def em_admin_update_table(refresh):
    """Load and display the emission data table."""
    path = DATA_DIR / "emission_report.csv"
    df = em_admin_read_csv_safely(path)
    return em_admin_create_editable_table(df)


@app.callback(
    Output("em-admin-upload-status", "children"),
    Output("em-admin-data-refresh", "data"),
    Output("em-admin-upload-csv", "contents"),
    Input("em-admin-upload-csv", "contents"),
    State("em-admin-upload-csv", "filename"),
    State("em-admin-data-refresh", "data"),
    prevent_initial_call=True,
)
def em_admin_handle_upload(contents, filename, refresh):
    """Handle CSV file upload."""
    if not contents:
        return dash.no_update, refresh, dash.no_update
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Try multiple encodings
        df = pd.DataFrame()
        for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            try:
                # First, read as raw to find the header
                raw_df = pd.read_csv(io.StringIO(decoded.decode(enc)), header=None, dtype=str)
                header_idx = -1
                for i, row in raw_df.iterrows():
                    if row.astype(str).str.contains('Department', case=False).any():
                        header_idx = i
                        break
                
                if header_idx != -1:
                    df = pd.read_csv(io.StringIO(decoded.decode(enc)), skiprows=header_idx)
                    df.columns = df.columns.astype(str).str.strip()
                    break
                else:
                    # Try reading without skip as fallback
                    df = pd.read_csv(io.StringIO(decoded.decode(enc)))
                    df.columns = df.columns.astype(str).str.strip()
                    break
            except:
                continue
        
        if df.empty:
            return "❌ Failed to read CSV. Check format/encoding.", refresh, dash.no_update
        
        # Save to emission_report.csv
        save_path = DATA_DIR / "emission_report.csv"
        em_admin_save_csv_safely(df, save_path)
        
        return f"✅ Uploaded {filename} successfully!", refresh + 1, None
        
    except Exception as e:
        return f"❌ Upload failed: {str(e)}", refresh, dash.no_update


@app.callback(
    Output("em-admin-save-status", "children"),
    Output("em-admin-data-refresh", "data", allow_duplicate=True),
    Input("em-admin-save-button", "n_clicks"),
    Input("em-admin-clear-button", "n_clicks"),
    Input("em-admin-apply-dates", "n_clicks"),
    State("em-admin-data-table", "data"),
    State("em-admin-date-start", "date"),
    State("em-admin-date-end", "date"),
    State("em-admin-data-refresh", "data"),
    prevent_initial_call=True,
)
def em_admin_handle_actions(save_clicks, clear_clicks, apply_clicks, table_data, start_date, end_date, refresh):
    """Handle save, clear, and date range actions."""
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update, refresh
    
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    path = DATA_DIR / "emission_report.csv"
    
    if trigger_id == "em-admin-save-button":
        if table_data is None:
            return "⚠ No data to save", refresh
        
        df = pd.DataFrame(table_data).fillna("")
        em_admin_save_csv_safely(df, path)
        return f"✅ Saved to {path.name}", refresh + 1
    
    elif trigger_id == "em-admin-clear-button":
        df = pd.DataFrame()
        em_admin_save_csv_safely(df, path)
        return "✅ Data cleared", refresh + 1
    
    elif trigger_id == "em-admin-apply-dates":
        if not start_date or not end_date:
            return "⚠ Please select both start and end dates", refresh
        
        df = em_admin_read_csv_safely(path)
        if df.empty:
            return "⚠ No data to filter", refresh
        
        # Filter data by date range
        try:
            # Parse dates from the Date column
            if 'Date' in df.columns:
                df['Date_parsed'] = pd.to_datetime(df['Date'], format='%d-%b-%Y', errors='coerce')
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                
                # Filter
                filtered_df = df[(df['Date_parsed'] >= start_dt) & (df['Date_parsed'] <= end_dt)]
                filtered_df = filtered_df.drop(columns=['Date_parsed'])
                
                em_admin_save_csv_safely(filtered_df, path)
                return f"✅ Filtered data from {start_date} to {end_date}", refresh + 1
            else:
                return "⚠ No 'Date' column found in data", refresh
        except Exception as e:
            return f"❌ Date filtering failed: {str(e)}", refresh
    
    return dash.no_update, refresh
