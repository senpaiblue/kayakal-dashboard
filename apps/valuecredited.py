import dash
from dash import html, dcc, Input, Output, State, dash_table, ctx, no_update
import pandas as pd
import os
import uuid
from datetime import date, datetime
import csv

dash.register_page(__name__, path="/valuecredited")

BASE_PATH = "./assets/K5"
VC_PENDING_CSV = "./Data/value_credited_pending.csv"
VC_PENDING_COLUMNS = ["id", "zone", "dept", "date", "item_name", "tonnage", "action", "status", "submitted_at"]

def _append_vc_pending(row_dict):
    exists = os.path.isfile(VC_PENDING_CSV) and os.path.getsize(VC_PENDING_CSV) > 0
    if exists:
        with open(VC_PENDING_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(VC_PENDING_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(VC_PENDING_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VC_PENDING_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)

# ---------- Layout ----------
layout = html.Div(
    [
        # Zone & Department banner
        html.Div(
            id="vc-zone-dept-info",
            style={
                "textAlign": "center",
                "fontWeight": "bold",
                "fontSize": "18px",
                "marginBottom": "15px",
            },
        ),

        html.H3("Value Credited Entry", style={"textAlign": "center"}),

        # ---------- ALL INPUTS IN ONE ROW ----------
        html.Div(
            [

                html.Div([
                    html.Label("Date"),
                    dcc.DatePickerSingle(
                        id="vc-date",
                        date=date.today(),
                        display_format="DD-MM-YYYY",
                    ),
                ], style={"width": "14%"}),

                html.Div([
                    html.Label("Item Name"),
                    dcc.Input(
                        id="vc-item-name",
                        type="text",
                        placeholder="Enter item name",
                        style={"width": "100%"},
                    ),
                ], style={"width": "14%"}),

                html.Div([
                    html.Label("Tonnage"),
                    dcc.Input(
                        id="vc-tonnage",
                        type="number",
                        step=0.01,
                        min=0,
                        style={"width": "100%"},
                    ),
                ], style={"width": "14%"}),

            ],
            style={
                "display": "flex",
                "gap": "10px",
                "justifyContent": "center",
                "alignItems": "flex-end",
                "marginTop": "20px",
                "flexWrap": "nowrap",
            },
        ),

        html.Br(),

        html.Div(
            [
                html.Button(
                    "Save for Approval",
                    id="vc-save-btn",
                    n_clicks=0,
                    style={
                        "padding": "8px 30px",
                        "fontWeight": "bold",
                        "backgroundColor": "#0d6efd",
                        "color": "white",
                        "border": "none",
                        "marginRight": "10px",
                    },
                ),
                html.Button(
                    "Delete Selected",
                    id="vc-del-btn",
                    n_clicks=0,
                    style={
                        "padding": "8px 30px",
                        "fontWeight": "bold",
                        "backgroundColor": "#dc3545",
                        "color": "white",
                        "border": "none",
                    },
                ),
            ],
            style={"textAlign": "center"},
        ),

        html.Br(),
        html.Div(id="vc-notification", style={"textAlign": "center"}),
        html.Div(id="vc-del-notification", style={"textAlign": "center", "marginTop": "10px"}),

        html.Hr(),

        dash_table.DataTable(
            id="vc-table",
            columns=[
                {"name": "Date", "id": "Date"},
                {"name": "Item Name", "id": "Item Name"},
                {"name": "Tonnage", "id": "Tonnage"},
            ],
            row_selectable="single",
            style_table={"width": "95%", "margin": "auto"},
            style_cell={
                "border": "1px solid #ccc",
                "padding": "6px",
                "textAlign": "center",
                "fontSize": "13px",
            },
            style_header={
                "backgroundColor": "#f1f1f1",
                "fontWeight": "bold",
            },
        ),
    ],
    style={"padding": "20px"},
)


# ---------- Zone & Department (FROM MAIN dcc.Store) ----------
@dash.callback(
    Output("vc-zone-dept-info", "children"),
    Input("active-zone", "data"),
    Input("active-department", "data"),
)
def update_zone_department(zone, department):
    if not zone or not department:
        return "⚠️ Zone / Department not selected"
    return f"Zone: {zone}   |   Department: {department}"

# ---------- Save (Add to Pending Queue) ----------
@dash.callback(
    Output("vc-notification", "children"),
    Input("vc-save-btn", "n_clicks"),
    State("vc-date", "date"),
    State("vc-item-name", "value"),
    State("vc-tonnage", "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def save_data(_, dt, item_name, tonnage, zone, department):
    if not all([dt, tonnage, zone, department]):
        return html.Span(
            "⚠️ All fields are mandatory",
            style={"color": "red", "fontWeight": "bold"},
        )

    _append_vc_pending({
        "id": str(uuid.uuid4())[:8],
        "zone": str(zone),
        "dept": str(department),
        "date": str(dt),
        "item_name": (item_name or "").strip(),
        "tonnage": str(round(float(tonnage), 2)),
        "action": "add",
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    })

    return html.Span(
        "✅ Submitted for Approval",
        style={"color": "green", "fontWeight": "bold"},
    )


# ---------- Delete (Add to Pending Queue) ----------
@dash.callback(
    Output("vc-del-notification", "children"),
    Input("vc-del-btn", "n_clicks"),
    State("vc-table", "selected_rows"),
    State("vc-table", "data"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def delete_data(_, selected_rows, table_data, zone, department):
    if not selected_rows or not table_data:
        return html.Span(
            "⚠️ Please select a row to delete",
            style={"color": "orange", "fontWeight": "bold"},
        )
        
    if not zone or not department:
        return html.Span("⚠️ Zone / Department not selected", style={"color": "red", "fontWeight": "bold"})

    row = table_data[selected_rows[0]]

    _append_vc_pending({
        "id": str(uuid.uuid4())[:8],
        "zone": str(zone),
        "dept": str(department),
        "date": str(row.get("Date", "")),
        "item_name": str(row.get("Item Name", "")).strip(),
        "tonnage": str(row.get("Tonnage", "")),
        "action": "delete",
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    })

    return html.Span(
        "✅ Deletion submitted for Approval",
        style={"color": "green", "fontWeight": "bold"},
    )


# ---------- Load Table ----------
_vc_table_cache = {}

@dash.callback(
    Output("vc-table", "data"),
    Output("vc-table", "selected_rows"),
    Input("vc-save-btn", "n_clicks"),
    Input("vc-del-btn", "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
)
def load_table(save_clicks, del_clicks, zone, department):
    if not zone or not department:
        return [], []

    from apps.progress import get_progress_folder
    folder = os.path.dirname(get_progress_folder(zone, department))
    path = os.path.join(folder, "value.csv")
    if not os.path.exists(path):
        return [], []

    try:
        mtime = os.path.getmtime(path)
        pending_mtime = os.path.getmtime(VC_PENDING_CSV) if os.path.isfile(VC_PENDING_CSV) else 0.0
        cache_key = (path, mtime, pending_mtime)
        if cache_key in _vc_table_cache:
            return _vc_table_cache[cache_key].copy(), []
    except Exception:
        cache_key = None

    df = pd.read_csv(path)
    
    # Filter out items that are pending deletion
    if os.path.isfile(VC_PENDING_CSV) and os.path.getsize(VC_PENDING_CSV) > 0:
        with open(VC_PENDING_CSV, newline="", encoding="utf-8") as f:
            pending_rows = list(csv.DictReader(f))
            
        for pr in pending_rows:
            if pr.get("status") == "pending" and pr.get("action") == "delete" and pr.get("zone") == zone and pr.get("dept") == department:
                t_date = pr.get("date", "")
                t_item = pr.get("item_name", "")
                try:
                    t_tonnage = float(pr.get("tonnage", 0))
                except ValueError:
                    t_tonnage = 0.0
                
                # Create a mask to drop the exact matching row
                mask = ~((df["Date"] == t_date) & 
                         (df["Item Name"] == t_item) & 
                         ((df["Tonnage"] - t_tonnage).abs() < 0.01))
                df = df[mask]

    records = df.to_dict("records")
    if cache_key is not None:
        _vc_table_cache[cache_key] = records.copy()

    return records, []
