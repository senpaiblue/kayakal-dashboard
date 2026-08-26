import dash
from dash import html, dcc, Input, Output, State, ALL
import dash_bootstrap_components as dbc
from app import app
import pandas as pd
import base64
import io
import os
import tempfile
import shutil
import re
from pathlib import Path
from datetime import datetime
from apps.dwm_parser import parse_dwm_excel, upsert_dwm_data

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
MONTHLY_CSV = DATA_DIR / "dwm_monthly.csv"
DAILY_CSV = DATA_DIR / "dwm_daily.csv"
UPLOAD_DIR = DATA_DIR / "dwm_uploaded_sheets"

def get_dwm_last_updated_str():
    if not MONTHLY_CSV.exists() and not DAILY_CSV.exists():
        return "No DWM data loaded yet"
    
    last_mod_time = 0
    if MONTHLY_CSV.exists():
        last_mod_time = max(last_mod_time, os.path.getmtime(MONTHLY_CSV))
    if DAILY_CSV.exists():
        last_mod_time = max(last_mod_time, os.path.getmtime(DAILY_CSV))
        
    return datetime.fromtimestamp(last_mod_time).strftime("%Y-%m-%d %H:%M:%S")

def get_dwm_current_data_preview():
    monthly_summary = html.Div("No monthly data available.")
    daily_summary = html.Div("No daily data available.")
    
    if MONTHLY_CSV.exists():
        try:
            df_m = pd.read_csv(MONTHLY_CSV)
            if not df_m.empty:
                monthly_summary = html.Div([
                    html.H5(f"Monthly KPIs Summary (Total: {len(df_m)} records)", className="mt-3"),
                    dbc.Table.from_dataframe(
                        df_m.head(10),
                        striped=True,
                        bordered=True,
                        hover=True,
                        size='sm',
                        style={'fontSize': '12px'}
                    )
                ])
        except Exception as e:
            monthly_summary = dbc.Alert(f"Error reading monthly CSV: {e}", color="danger")
            
    if DAILY_CSV.exists():
        try:
            df_d = pd.read_csv(DAILY_CSV)
            if not df_d.empty:
                daily_summary = html.Div([
                    html.H5(f"Daily KPIs Summary (Total: {len(df_d)} records)", className="mt-3"),
                    dbc.Table.from_dataframe(
                        df_d.head(10),
                        striped=True,
                        bordered=True,
                        hover=True,
                        size='sm',
                        style={'fontSize': '12px'}
                    )
                ])
        except Exception as e:
            daily_summary = dbc.Alert(f"Error reading daily CSV: {e}", color="danger")
            
    return html.Div([monthly_summary, html.Hr(), daily_summary])

layout = html.Div([
    html.H2("Daily Management (DWM) Data Management", style={"marginBottom": "30px", "color": "#0d6efd"}),
    
    dbc.Tabs(id="dwm-admin-tabs", active_tab="admin-tab-upload", children=[
        dbc.Tab(label="📊 Data Summary", tab_id="admin-tab-upload", tab_style={"cursor": "pointer"}),
        dbc.Tab(label="🗑️ Deletion Approvals", tab_id="admin-tab-delete", tab_style={"cursor": "pointer"}),
    ], className="mb-4"),
    
    html.Div(id="dwm-admin-tab-content")
], style={"padding": "20px"})


# -------------------------------------------------------------
# CALLBACK: Render DWM Admin Tab content
# -------------------------------------------------------------
@app.callback(
    Output("dwm-admin-tab-content", "children"),
    Input("dwm-admin-tabs", "active_tab")
)
def dwm_admin_switch_tab(active_tab):
    if active_tab == "admin-tab-upload":
        return html.Div([
            html.Div([
                html.P("View consolidated monthly trends and daily run chart data previews below.",
                       style={"fontSize": "16px", "color": "#666", "marginBottom": "15px"}),
                
                html.Div([
                    html.Span("Last Consolidated CSV Update: ", style={"color": "#666"}),
                    html.B(id="dwm-last-updated-date", children=get_dwm_last_updated_str(), style={"color": "#333"})
                ], className="mb-4"),
                
                html.H4("Consolidated Data Previews", style={"marginBottom": "20px", "color": "#333"}),
                html.Div(id='current-dwm-preview', children=get_dwm_current_data_preview())
                
            ], style={"padding": "20px", "maxWidth": "1200px", "backgroundColor": "white", "borderRadius": "8px", "border": "1px solid #d0d7de"})
        ])
    elif active_tab == "admin-tab-delete":
        return make_deletion_approvals_view()
    return html.Div()


def make_deletion_approvals_view():
    req_file = DATA_DIR / "dwm_delete_requests.csv"
    
    if not req_file.exists():
        return html.Div([
            dbc.Alert("No deletion requests submitted yet.", color="info", style={"borderRadius": "8px"})
        ], style={"maxWidth": "1200px"})
        
    try:
        df = pd.read_csv(req_file)
    except Exception as e:
        return html.Div([
            dbc.Alert(f"Error reading deletion requests: {e}", color="danger")
        ])
        
    # We only show Pending requests
    df_pending = df[df['status'] == 'Pending']
    
    if df_pending.empty:
        return html.Div([
            dbc.Alert("No pending deletion requests.", color="success", style={"borderRadius": "8px"})
        ], style={"maxWidth": "1200px"})
        
    # Build list of pending requests
    rows = []
    for idx, row in df_pending.iterrows():
        dept = row['department']
        req_time = row['requested_at']
        
        rows.append(html.Tr([
            html.Td(dept, style={"fontWeight": "600", "verticalAlign": "middle"}),
            html.Td(req_time, style={"verticalAlign": "middle"}),
            html.Td([
                dbc.Button("Approve Deletion", id={"type": "dwm-btn-approve", "index": dept}, color="danger", size="sm", className="me-2", style={"borderRadius": "6px"}),
                dbc.Button("Reject Deletion", id={"type": "dwm-btn-reject", "index": dept}, color="secondary", size="sm", style={"borderRadius": "6px"})
            ], style={"textAlign": "right"})
        ]))
        
    table = dbc.Table([
        html.Thead(html.Tr([
            html.Th("Department Name"),
            html.Th("Requested At"),
            html.Th("Actions", style={"textAlign": "right"})
        ])),
        html.Tbody(rows)
    ], striped=True, bordered=True, hover=True, style={"fontSize": "14px"})
    
    return html.Div([
        html.H4("Pending Department Deletion Requests", style={"color": "#333", "marginBottom": "20px"}),
        html.Div(id="dwm-delete-action-status"),
        table
    ], style={"padding": "20px", "maxWidth": "1200px", "backgroundColor": "white", "borderRadius": "8px", "border": "1px solid #d0d7de"})


# -------------------------------------------------------------
# CALLBACK: Handle Approval / Rejection of Deletion Requests
# -------------------------------------------------------------
@app.callback(
    Output("dwm-admin-tab-content", "children", allow_duplicate=True),
    Input({"type": "dwm-btn-approve", "index": ALL}, "n_clicks"),
    Input({"type": "dwm-btn-reject", "index": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_dwm_deletion_request(approve_clicks, reject_clicks):
    ctx = dash.callback_context
    if not ctx.triggered:
        return dash.no_update
        
    # Find which button was clicked
    triggered_id = ctx.triggered_id
    
    if not triggered_id:
        return dash.no_update
        
    trigger_val = ctx.triggered[0].get("value")
    if trigger_val is None or trigger_val == 0:
        return dash.no_update
        
    dept_name = triggered_id.get("index")
    action_type = triggered_id.get("type") # 'dwm-btn-approve' or 'dwm-btn-reject'
    
    req_file = DATA_DIR / "dwm_delete_requests.csv"
    
    if not req_file.exists():
        return dash.no_update
        
    try:
        df = pd.read_csv(req_file)
    except Exception as e:
        print(f"Error reading delete requests CSV: {e}")
        return dash.no_update
        
    if action_type == "dwm-btn-approve":
        # 1. Update CSV requests status case-insensitively
        df.loc[(df['department'].astype(str).str.strip().str.lower() == dept_name.strip().lower()) & (df['status'] == 'Pending'), 'status'] = 'Approved'
        df.to_csv(req_file, index=False)
        
        # 2. Delete department data from daily and monthly consolidated CSVs case-insensitively
        if MONTHLY_CSV.exists():
            try:
                df_m = pd.read_csv(MONTHLY_CSV)
                df_m = df_m[df_m['department'].astype(str).str.strip().str.lower() != dept_name.strip().lower()]
                df_m.to_csv(MONTHLY_CSV, index=False)
            except Exception as e:
                print(f"Error deleting monthly data for {dept_name}: {e}")
                
        if DAILY_CSV.exists():
            try:
                df_d = pd.read_csv(DAILY_CSV)
                df_d = df_d[df_d['department'].astype(str).str.strip().str.lower() != dept_name.strip().lower()]
                df_d.to_csv(DAILY_CSV, index=False)
            except Exception as e:
                print(f"Error deleting daily data for {dept_name}: {e}")
                
        # 3. Delete directory Data/dwm_uploaded_csvs/{dept_clean}/ case-insensitively
        try:
            parent_dir = DATA_DIR / "dwm_uploaded_csvs"
            if parent_dir.exists():
                dept_clean_lower = re.sub(r'[^a-zA-Z0-9_]', '_', dept_name.strip().lower())
                for item in parent_dir.iterdir():
                    if item.is_dir():
                        item_clean_lower = re.sub(r'[^a-zA-Z0-9_]', '_', item.name.strip().lower())
                        if item_clean_lower == dept_clean_lower:
                            shutil.rmtree(item)
        except Exception as e:
            print(f"Error deleting CSV folder for {dept_name}: {e}")
            
    elif action_type == "dwm-btn-reject":
        # Update requests status to Rejected case-insensitively
        df.loc[(df['department'].astype(str).str.strip().str.lower() == dept_name.strip().lower()) & (df['status'] == 'Pending'), 'status'] = 'Rejected'
        df.to_csv(req_file, index=False)
        
    # Return refreshed view
    return make_deletion_approvals_view()
