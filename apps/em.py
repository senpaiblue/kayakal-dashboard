import os
import base64
import concurrent.futures
import requests
import dash
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, no_update
from pathlib import Path
from datetime import datetime, date, timedelta
from urllib.parse import quote

from app import app

DATA_DIR = Path("./Data")

# ── DocketRun API configuration ──────────────────────────────────────────────
DR_BASE_URL = "http://10.10.89.165:8500/api"
DR_HEADERS  = {"x-api-key": "7f3d9c2a1e8b4f6a9d0c3e7b2a5f8c1d"}


def em_dr_fetch_summary(start_date=None, end_date=None):
    """Call /docketrun/summaryData and return the JSON dict or None on error."""
    params = {}
    if start_date:
        params["analytics_start_time"] = f"{start_date} 00:00:00"
    if end_date:
        params["analytics_stop_time"]  = f"{end_date} 23:59:59"
    try:
        resp = requests.get(
            f"{DR_BASE_URL}/docketrun/summaryData",
            headers=DR_HEADERS,
            params=params,
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"[DocketRun] summaryData HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[DocketRun] summaryData error: {exc}")
    return None


def em_dr_fetch_collection(department=None, camera_name=None, roi_name=None,
                           start_date=None, end_date=None):
    """Call /docketrun/collectionData and return the JSON dict or None on error.

    The API returns:
      {
        "used_payload": {...},
        "data": [ <camera-group objects> ]
      }
    All parameters are optional filters.
    """
    params = {}
    if department:
        params["department"]  = department
    if camera_name:
        params["camera_name"] = camera_name
    if roi_name:
        params["roi_name"]    = roi_name
    if start_date:
        params["analytics_start_time"] = f"{start_date} 00:00:00"
    if end_date:
        params["analytics_stop_time"]  = f"{end_date} 23:59:59"
    try:
        resp = requests.get(
            f"{DR_BASE_URL}/docketrun/collectionData",
            headers=DR_HEADERS,
            params=params,
            timeout=30,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"[DocketRun] collectionData HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[DocketRun] collectionData error: {exc}")
    return None


def em_dr_image_src(image_name):
    """Fetch /docketrun/getImage/:imageName and return a base-64 data-URI or None."""
    if not image_name:
        return None
    try:
        safe_name = quote(str(image_name), safe="")
        resp = requests.get(
            f"{DR_BASE_URL}/docketrun/getImage/{safe_name}",
            headers=DR_HEADERS,
            timeout=15,
            allow_redirects=True,
        )
        if resp.status_code == 200:
            ctype = resp.headers.get("Content-Type", "image/jpeg")
            b64   = base64.b64encode(resp.content).decode()
            return f"data:{ctype};base64,{b64}"
    except Exception as exc:
        print(f"[DocketRun] getImage error: {exc}")
    return None

def em_dash_read_emission_csv():
    """Read and parse the emission CSV file, handling the complex header structure."""
    csv_path = DATA_DIR / "emission_report.csv"
    
    if not csv_path.exists():
        return pd.DataFrame()
    
    try:
        # Read the file normally first to find where the actual table starts
        # We look for the row that contains 'Department'
        for enc in ['utf-8', 'utf-8-sig', 'cp1252', 'latin1']:
            try:
                # Read without skipping to find the header
                raw_df = pd.read_csv(csv_path, encoding=enc, header=None, dtype=str)
                header_idx = -1
                for i, row in raw_df.iterrows():
                    if row.astype(str).str.contains('Department', case=False).any():
                        header_idx = i
                        break
                
                if header_idx != -1:
                    # Re-read from that row
                    df = pd.read_csv(csv_path, skiprows=header_idx, encoding=enc)
                    break
                else:
                    # Fallback to current logic or try another encoding
                    continue
            except:
                continue
        else:
            return pd.DataFrame()
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return pd.DataFrame()
    
    # Clean column names
    df.columns = df.columns.astype(str).str.strip()
    
    # Keep only required columns and drop any unnamed columns
    required_cols = ['Department', 'Source', 'Date', 'Daily Count', 'Total Violations']
    # Keep these main columns, plus Image if it exists (but drop Unnamed columns)
    cols_to_keep = [col for col in df.columns if col in required_cols or col == 'Image']
    if cols_to_keep:
        df = df[cols_to_keep]
    
    # Fill forward the Department, Source, and Total Violations columns
    # (they only appear on the first row of each group)
    if 'Department' in df.columns:
        df['Department'] = df['Department'].replace('', pd.NA).replace('nan', pd.NA).ffill()
    if 'Source' in df.columns:
        df['Source'] = df['Source'].replace('', pd.NA).replace('nan', pd.NA).ffill()
    if 'Total Violations' in df.columns:
        df['Total Violations'] = df['Total Violations'].replace('', pd.NA).replace('nan', pd.NA).ffill()
    
    # Remove rows where Date is empty
    if 'Date' in df.columns:
        df = df.dropna(subset=['Date'])
    
    return df


def em_dash_get_departments():
    """Get list of unique departments from the emission data."""
    df = em_dash_read_emission_csv()
    if df.empty or 'Department' not in df.columns:
        return []
    
    departments = sorted(df['Department'].dropna().unique().tolist())
    return [d for d in departments if str(d).strip()]


layout = dbc.Container([
    html.H2("Emission Control Dashboard", className="mt-3 mb-4"),

    # ── CSV-based section ──────────────────────────────────────────────────────
    # dbc.Row([
    #     dbc.Col([
    #         dbc.Label("Select Department"),
    #         dcc.Dropdown(
    #             id="em-dash-department-dropdown",
    #             placeholder="Select a department...",
    #             className="mb-3"
    #         ),
    #     ], md=6),
    # ]),

    # Summary Card
    html.Div(id="em-dash-summary-card", className="mb-4"),

    # Trend Graph — auto-refreshes from DocketRun API every 2 minutes
    dbc.Row([
        dbc.Col([
            dbc.Row([
                dbc.Col(html.H4("Daily Count Trend by Source", className="mb-0"), width="auto"),
                dbc.Col(
                    html.Small(id="em-dash-last-refresh", className="text-muted ms-2",
                               style={"lineHeight": "2.2"}),
                    width="auto"
                ),
            ], align="center", className="mb-3"),
            # Original bar chart
            dcc.Graph(
                id="em-dash-trend-graph",
                style={"height": "400px"},
                config={"displayModeBar": False},
            ),
            html.Hr(className="my-4"),
            html.H5("Violation Trend — Dotted View", className="mb-3"),
            
            # NEW TABS OVER THE DOT GRAPH
            dbc.Tabs(id="em-dash-dept-tabs", active_tab="All", className="mb-3"),

            # New dotted/scatter chart
            dcc.Graph(
                id="em-dash-trend-dot-graph",
                style={"height": "400px"},
                config={"displayModeBar": False},
            ),
        ], md=12),
    ], className="mb-4"),

    # Data Table
    # dbc.Row([
    #     dbc.Col([
    #         html.H4("Detailed Data", className="mb-3"),
    #         html.Div(id="em-dash-data-table"),
    #     ], md=12),
    # ]),

    # Store for CSV-based drill-down data
    dcc.Store(id="em-dash-data-store"),
    # Store for DocketRun API live summary (used by trend graph)
    dcc.Store(id="em-dash-api-store"),
    # Auto-refresh interval: every 2 minutes = 120_000 ms
    dcc.Interval(id="em-dash-refresh-interval", interval=120_000, n_intervals=0),

    html.Hr(className="my-5"),

    # Container for live details based on tab click
    html.Div(id="em-dr-dept-details-area", children=[
        # Collection results (table + stats)
        html.Div(id="em-dr-collection-area", className="mb-4"),
        # Image viewer
        html.Div(id="em-dr-image-viewer"),
    ]),

    # Hidden stores
    dcc.Store(id="em-dash-weekly-data-store"),
    dcc.Store(id="em-dash-dept-mapping"),
    dcc.Store(id="em-dr-collection-store"),
    dcc.Store(id="em-dr-selected-image"),

], fluid=True)


@app.callback(
    Output("em-dash-department-dropdown", "options"),
    Input("em-dash-department-dropdown", "id"),
)
def em_dash_populate_dropdown(_):
    """Populate department dropdown options dynamically."""
    departments = em_dash_get_departments()
    return [{"label": dept, "value": dept} for dept in departments]


@app.callback(
    Output("em-dash-data-store", "data"),
    Output("em-dash-summary-card", "children"),
    Input("em-dash-department-dropdown", "value"),
)
def em_dash_update_data_and_summary(selected_dept):
    """Load data for selected department and create summary card."""
    if not selected_dept:
        return None, dbc.Alert("Please select a department to view emission data.", color="info")
    
    df = em_dash_read_emission_csv()
    if df.empty:
        return None, dbc.Alert("No emission data available. Please upload data via admin panel.", color="warning")
    
    # Filter by department
    dept_df = df[df['Department'] == selected_dept].copy()
    
    if dept_df.empty:
        return None, dbc.Alert(f"No data found for department: {selected_dept}", color="warning")
    
    # Get total violations
    total_violations = dept_df['Total Violations'].iloc[0] if 'Total Violations' in dept_df.columns else "N/A"
    
    # Create summary card
    summary_card = dbc.Card([
        dbc.CardBody([
            html.H3(selected_dept, className="card-title"),
            html.H4(f"Total Violations: {total_violations}", className="text-primary"),
            html.P(f"Data points: {len(dept_df)}", className="text-muted"),
        ])
    ], className="mb-3", color="light")
    
    # Return data as JSON for the graph callback
    return dept_df.to_json(date_format='iso', orient='split'), summary_card


@app.callback(
    Output("em-dash-trend-graph",    "figure"),
    Output("em-dash-api-store",      "data"),
    Output("em-dash-last-refresh",   "children"),
    Input("em-dash-refresh-interval", "n_intervals"),
)
def em_dash_update_trend_graph(_n):
    """Fetch today's violation summary from DocketRun and draw the trend bar chart."""
    today = datetime.now().strftime("%Y-%m-%d")
    data  = em_dr_fetch_summary(start_date=today, end_date=today)

    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )

    refresh_label = f"Last refreshed: {datetime.now().strftime('%H:%M:%S')}"

    if data is None:
        empty_fig.update_layout(title="API unavailable – retrying in 2 mins")
        return empty_fig, None, refresh_label

    departments = data.get("summary", {}).get("departments", [])
    if not departments:
        empty_fig.update_layout(title="No violation data for today")
        return empty_fig, data, refresh_label

    # Build rows: one per dept → camera → roi
    rows = []
    for dept in departments:
        dept_name  = dept["department_name"]
        dept_total = dept["total_documents"]
        for cam in dept.get("cameras", []):
            cam_name  = cam["camera_name"]
            cam_total = cam["total_documents"]
            for roi in cam.get("roi_names", []):
                rows.append({
                    "Department": dept_name,
                    "Camera":     cam_name,
                    "ROI":        roi["roi_name"],
                    "Violations": roi["document_count"],
                })

    df_plot = pd.DataFrame(rows)

    # Group → one bar per Camera+ROI, coloured by Department
    fig = go.Figure()
    colors = [
        "#e63946", "#2a9d8f", "#e9c46a", "#264653",
        "#f4a261", "#457b9d", "#a8dadc", "#6a4c93",
        "#1982c4", "#8ac926"
    ]
    color_map = {
        dept: colors[i % len(colors)]
        for i, dept in enumerate(df_plot["Department"].unique())
    }

    for dept_name, grp in df_plot.groupby("Department"):
        labels = grp["Camera"] + " / " + grp["ROI"]
        fig.add_trace(go.Bar(
            y=labels,
            x=grp["Violations"],
            name=dept_name,
            orientation="h",
            marker_color=color_map[dept_name],
            hovertemplate=(
                f"<b>{dept_name}</b><br>"
                "%{y}<br>"
                "Violations: %{x}<extra></extra>"
            ),
        ))

    fig.update_layout(
        title=dict(
            text=f"Today's Violations by Camera / ROI  ·  {today}",
            font=dict(size=14),
        ),
        barmode="stack",
        xaxis_title="Violation Count",
        yaxis_title="",
        yaxis=dict(autorange="reversed"),
        template="plotly_white",
        height=400,
        margin=dict(l=10, r=10, t=50, b=30),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
    )

    return fig, data, refresh_label


@app.callback(
    Output("em-dash-weekly-data-store", "data"),
    Output("em-dash-dept-tabs", "children"),
    Output("em-dash-dept-mapping", "data"),
    Input("em-dash-refresh-interval", "n_intervals"),
)
def em_dash_fetch_weekly_trend_data(_n):
    """Fetch 7 days of violation summary into a cached store."""
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=6)
    dates_to_fetch = [(start_dt + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]
    
    daily_results = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=7) as executor:
        future_to_date = {
            executor.submit(em_dr_fetch_summary, d, d): d 
            for d in dates_to_fetch
        }
        for future in concurrent.futures.as_completed(future_to_date):
            d = future_to_date[future]
            try:
                data = future.result()
                if data:
                    daily_results[d] = data
            except Exception as exc:
                print(f"[DocketRun] em_dr_fetch_summary error for {d}: {exc}")

    rows = []
    dept_map = {}
    
    for d in dates_to_fetch:
        data = daily_results.get(d)
        if not data:
            continue
            
        departments = data.get("summary", {}).get("departments", [])
        day_dept_totals = {}
        day_orig_depts = {}
        
        for dept in departments:
            orig_dept_name = dept["department_name"]
            
            # Apply grouping logic
            name_upper = orig_dept_name.upper()
            if "BF-1" in name_upper or "BF-5" in name_upper or "BF1" in name_upper:
                dept_name = "Blast Furnace"
            elif "SMS" in name_upper:
                dept_name = "SMS"
            elif "RMHS" in name_upper:
                dept_name = "RMHS"
            elif "CO" in name_upper:
                dept_name = "CO"
            elif "IST" in name_upper:
                dept_name = "IST"
            else:
                dept_name = orig_dept_name

            if dept_name not in dept_map:
                dept_map[dept_name] = set()
            dept_map[dept_name].add(orig_dept_name)

            total_docs = dept.get("total_documents", 0)
            
            if dept_name not in day_dept_totals:
                day_dept_totals[dept_name] = 0
                day_orig_depts[dept_name] = orig_dept_name
            day_dept_totals[dept_name] += total_docs
            
        for dept_name, count in day_dept_totals.items():
            if count > 0:
                rows.append({
                    "Date": d,
                    "GroupedDept": dept_name,
                    "OriginalDept": day_orig_depts[dept_name],
                    "Violations": count,
                })

    dept_map_json = {k: list(v) for k, v in dept_map.items()}
    tab_children = [dbc.Tab(label="All", tab_id="All")] + [
        dbc.Tab(label=grp, tab_id=grp) for grp in sorted(dept_map_json.keys())
    ]
    
    return rows, tab_children, dept_map_json


@app.callback(
    Output("em-dash-trend-dot-graph", "figure"),
    Input("em-dash-weekly-data-store", "data"),
    Input("em-dash-dept-tabs", "active_tab"),
)
def em_dash_render_trend_dot_graph(rows, active_tab):
    empty_dot_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=30, b=0),
        height=400,
    )
    
    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=6)
    end_str = end_dt.strftime("%Y-%m-%d")
    start_str = start_dt.strftime("%Y-%m-%d")
    
    if not rows:
        empty_dot_fig.update_layout(title="No violation data for the past 7 days")
        return empty_dot_fig

    df_dot = pd.DataFrame(rows)
    
    colors = [
        "#e63946", "#2a9d8f", "#e9c46a", "#264653",
        "#f4a261", "#457b9d", "#a8dadc", "#6a4c93",
        "#1982c4", "#8ac926"
    ]
    # Keep color mapping consistent even when filtering
    all_depts = sorted(list(df_dot["GroupedDept"].unique()))
    color_map = {dept: colors[i % len(colors)] for i, dept in enumerate(all_depts)}

    if active_tab and active_tab != "All":
        df_dot = df_dot[df_dot["GroupedDept"] == active_tab]
        
    if df_dot.empty:
        empty_dot_fig.update_layout(title=f"No violation data for {active_tab} over past 7 days")
        return empty_dot_fig

    dot_fig = go.Figure()
    for dept_name, grp in df_dot.groupby("GroupedDept"):
        grp_sorted = grp.sort_values(by="Date").reset_index(drop=True)
        
        text_labels = ["" for _ in range(len(grp_sorted))]
        if len(grp_sorted) > 0:
            text_labels[-1] = f" <b>{dept_name}</b>" # add text to the last chronological point
            
        dot_fig.add_trace(go.Scatter(
            x=grp_sorted["Violations"], 
            y=grp_sorted["Date"],
            mode="lines+markers+text",
            text=text_labels,
            textposition="middle right",
            name=dept_name,
            customdata=grp_sorted[["GroupedDept", "OriginalDept"]].values, # customdata for callback
            marker=dict(
                color=color_map[dept_name],
                size=12,
                symbol="circle",
                line=dict(width=1, color="white"),
            ),
            line=dict(
                color=color_map[dept_name],
                width=2
            ),
            hovertemplate=(
                f"<b>{dept_name}</b> (Orig: %{{customdata[1]}})<br>"
                "Date: %{y}<br>"
                "Violations: %{x}<extra></extra>"
            ),
        ))

    dot_fig.update_layout(
        title=dict(
            text=f"7-Day Violations Dotted View · {start_str} to {end_str}",
            font=dict(size=14),
        ),
        xaxis_title="Violation Count",
        yaxis_title="Date",
        template="plotly_white",
        height=400,
        margin=dict(l=10, r=100, t=50, b=50), # added right margin for text
        showlegend=False, 
    )

    return dot_fig


@app.callback(
    Output("em-dash-data-table", "children"),
    Input("em-dash-data-store", "data"),
)
def em_dash_update_data_table(data_json):
    """Display detailed data table."""
    if not data_json:
        return html.P("No data to display", className="text-muted")
    
    # Load data from JSON
    dept_df = pd.read_json(data_json, orient='split')
    
    # Select relevant columns
    display_cols = ['Source', 'Date', 'Daily Count']
    display_df = dept_df[display_cols].copy()
    
    # Create table
    table = dbc.Table.from_dataframe(
        display_df,
        striped=True,
        bordered=True,
        hover=True,
        responsive=True,
        size='sm',
        className="mt-2"
    )
    
    return table


# ─────────────────────────────────────────────────────────────────────────────
# DocketRun callbacks (all IDs prefixed em-dr- to avoid conflicts)
# ─────────────────────────────────────────────────────────────────────────────

@app.callback(
    Output("em-dr-collection-store", "data"),
    Output("em-dr-collection-area",  "children"),
    Output("em-dr-image-viewer",     "children"),
    Input("em-dash-dept-tabs", "active_tab"),
    State("em-dash-dept-mapping", "data"),
    prevent_initial_call=False,
)
def em_dr_load_collection(active_tab, dept_mapping):
    """Fetch collectionData and display a summary table + image grid based on the active tab."""
    if not active_tab or not dept_mapping:
        return None, "", ""

    end_dt = datetime.now()
    start_dt = end_dt - timedelta(days=6)
    start_date = start_dt.strftime("%Y-%m-%d")
    end_date = end_dt.strftime("%Y-%m-%d")

    orig_depts = []
    if active_tab == "All":
        for val in dept_mapping.values():
            orig_depts.extend(val)
    else:
        orig_depts = dept_mapping.get(active_tab, [])
        
    if not orig_depts:
        return None, "", ""
        
    items = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = [
            executor.submit(em_dr_fetch_collection, od, None, None, start_date, end_date)
            for od in orig_depts
        ]
        for future in concurrent.futures.as_completed(futures):
            try:
                col_data = future.result()
                if col_data and isinstance(col_data, dict) and "data" in col_data:
                    items.extend(col_data["data"])
            except Exception:
                pass

    if not items:
        return None, dbc.Alert(f"No records found for {active_tab} in the last 7 days.", color="info"), ""

    data = {"data": items}

    # ── Aggregate totals across all items ────────────────────────────────────
    total_docs       = sum(it.get("total_count",      0) for it in items)
    total_violations = sum(it.get("total_violations", 0) for it in items)
    num_cameras      = len({it.get("camera_name", "") for it in items})

    # ── KPI cards ────────────────────────────────────────────────────────────
    stats_cards = dbc.Row([
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Total Records", className="text-muted"),
            html.H4(str(total_docs), className="fw-bold mb-0 text-primary"),
        ]), color="light"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Total Violations", className="text-muted"),
            html.H4(str(total_violations), className="fw-bold mb-0 text-danger"),
        ]), color="light"), md=3),
        dbc.Col(dbc.Card(dbc.CardBody([
            html.Small("Camera / ROI Groups", className="text-muted"),
            html.H4(str(len(items)), className="fw-bold mb-0"),
        ]), color="light"), md=3),
    ], className="g-2 mb-4")

    # ── Summary table (one row per camera-ROI group) ──────────────────────────
    table_rows = []
    for it in items:
        gs   = it.get("group_summary", {})
        rate = it.get("violation_rate", gs.get("violation_rate", ""))
        table_rows.append(html.Tr([
            html.Td(str(it.get("SNo", ""))),
            html.Td(it.get("camera_name", "")),
            html.Td(it.get("department", "")),
            html.Td(it.get("roi_name", "")),
            html.Td(str(it.get("total_count", gs.get("total_count", "")))),
            html.Td(str(it.get("total_violations", gs.get("violations", "")))),
            html.Td(f"{rate}%" if rate != "" else ""),
        ]))

    summary_table = dbc.Table(
        [
            html.Thead(html.Tr([
                html.Th("#"), html.Th("Camera"), html.Th("Department"),
                html.Th("ROI"), html.Th("Records"), html.Th("Violations"),
                html.Th("Violation Rate"),
            ])),
            html.Tbody(table_rows),
        ],
        striped=True, bordered=True, hover=True, responsive=True, size="sm",
        className="mb-4",
    )

    # ── Image grid ───────────────────────────────────────────────────────────
    # Collect (image_name, roi_label, camera_label, timestamp) per image object.
    all_image_info = []
    for it in items:
        roi_label = it.get("roi_name", "")
        cam_label = it.get("camera_name", "")
        for img_obj in it.get("images", []):
            # image name lives in obj_details[0]["image_name"]
            obj_details = img_obj.get("obj_details", [])
            img_name = ""
            timestamp = ""
            confidence = ""
            if obj_details:
                img_name   = obj_details[0].get("image_name", "")
                timestamp  = obj_details[0].get("timestamp", "")
                confidence = obj_details[0].get("confidence", "")
            if not img_name:
                # fall back to available_image at the group level
                img_name = it.get("available_image", "")
            if img_name:
                all_image_info.append({
                    "name":       img_name,
                    "roi":        roi_label,
                    "camera":     cam_label,
                    "timestamp":  timestamp,
                    "confidence": confidence,
                })

    image_cards = []
    for info in all_image_info[:30]:   # cap at 30 to avoid huge payloads
        img_name   = info["name"]
        roi_label  = info["roi"]
        cam_label  = info["camera"]
        ts_label   = str(info["timestamp"]).replace("T", " ") if info["timestamp"] else ""
        conf_label = f"Conf: {info['confidence']:.0%}" if isinstance(info["confidence"], float) else ""

        src = em_dr_image_src(img_name)
        if src:
            img_el = html.Img(
                src=src,
                style={"width": "100%", "height": "160px", "objectFit": "cover",
                       "borderRadius": "6px"},
            )
        else:
            img_el = html.Div(
                "Image unavailable",
                style={"width": "100%", "height": "160px", "background": "#e9ecef",
                       "display": "flex", "alignItems": "center",
                       "justifyContent": "center", "borderRadius": "6px",
                       "color": "#666", "fontSize": "0.8rem"},
            )

        card = dbc.Col(
            dbc.Card([
                dbc.CardBody([
                    img_el,
                    html.Small(
                        img_name,
                        className="text-muted d-block mt-1",
                        style={"fontSize": "0.65rem", "wordBreak": "break-all"},
                    ),
                    html.Small(f"📷 {cam_label}  |  🗺 {roi_label}",
                               className="d-block text-secondary",
                               style={"fontSize": "0.7rem"}),
                    html.Small(
                        " · ".join(filter(None, [ts_label, conf_label])),
                        className="d-block text-muted",
                        style={"fontSize": "0.65rem"},
                    ),
                ], className="p-2"),
            ], className="h-100 shadow-sm"),
            md=3, className="mb-3"
        )
        image_cards.append(card)

    if not image_cards:
        image_grid = dbc.Alert("No images found in this collection.", color="info")
    else:
        image_grid = dbc.Row(image_cards, className="g-2")

    heading_text = f"Violation Images — {active_tab}"

    collection_area = html.Div([stats_cards, summary_table])
    image_viewer = html.Div([
        html.H5(heading_text, className="mb-3"),
        image_grid,
    ])

    return data, collection_area, image_viewer
