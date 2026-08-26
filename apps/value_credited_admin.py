import os
import csv
import dash
from dash import html, dcc, Input, Output, State, ctx, MATCH, dash_table
import dash_bootstrap_components as dbc
from datetime import datetime
import pandas as pd

dash.register_page(__name__, path="/value-credited-admin")

BASE_PATH = "./assets/K5"
VC_PENDING_CSV = "./Data/value_credited_pending.csv"
VC_PENDING_COLUMNS = ["id", "zone", "dept", "date", "item_name", "tonnage", "action", "status", "submitted_at"]

def _read_vc_pending(zone=None, dept=None):
    if not os.path.isfile(VC_PENDING_CSV) or os.path.getsize(VC_PENDING_CSV) == 0:
        return []
    with open(VC_PENDING_CSV, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
        
    rows = [r for r in rows if r.get("status") == "pending"]
    if zone:
        rows = [r for r in rows if r.get("zone") == zone]
    if dept:
        rows = [r for r in rows if r.get("dept") == dept]
    return rows

def _write_vc_pending(rows):
    with open(VC_PENDING_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=VC_PENDING_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in VC_PENDING_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)


def _build_card(row):
    uid = row["id"]
    action = row.get("action", "add").lower()
    
    action_color = "success" if action == "add" else "danger"
    action_text = "ADDITION" if action == "add" else "DELETION"

    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.H5([
                        html.Span(f"Request: {action_text}", className=f"text-{action_color} fw-bold me-2"),
                    ]),
                    html.Hr(),
                    html.Div([
                        html.Span("Zone: ", className="fw-bold"),
                        html.Span(row.get("zone", "")),
                    ]),
                    html.Div([
                        html.Span("Department: ", className="fw-bold"),
                        html.Span(row.get("dept", "")),
                    ]),
                    html.Div([
                        html.Span("Date: ", className="fw-bold"),
                        html.Span(row.get("date", "")),
                    ]),
                    html.Div([
                        html.Span("Item Name: ", className="fw-bold"),
                        html.Span(row.get("item_name", "")),
                    ]),
                    html.Div([
                        html.Span("Tonnage: ", className="fw-bold"),
                        html.Span(row.get("tonnage", "")),
                    ]),
                    html.Div([
                        html.Span("Submitted: ", className="fw-bold"),
                        html.Span(row.get("submitted_at", "")),
                    ], className="text-muted small mt-2"),

                    html.Div([
                        dbc.Button(
                            "✔ Approve",
                            id={"type": "vcadmin-approve-btn", "uid": uid},
                            color="success",
                            size="sm",
                            className="me-2",
                        ),
                        dbc.Button(
                            "✘ Reject",
                            id={"type": "vcadmin-reject-btn", "uid": uid},
                            color="danger",
                            size="sm",
                        ),
                    ], className="mt-3"),
                ], md=12),
            ]),
            html.Div(id={"type": "vcadmin-result", "uid": uid}, className="mt-2"),
        ]),
        className="mb-3 shadow-sm",
    )


layout = dbc.Container([
    html.H4("Value Credited Entry — Approvals", className="mt-3 mb-3 text-primary"),
    html.Div([
        dcc.Link(
            dbc.Button("← Progress Approvals", color="primary", size="sm"),
            href="/progress-admin",
        ),
        dcc.Link(
            dbc.Button("Red Tag Approvals →", color="danger", size="sm", className="ms-2"),
            href="/red-tag-admin",
        ),
        dcc.Link(
            dbc.Button("Greenery Approvals →", color="success", size="sm", className="ms-2"),
            href="/greenery-admin",
        ),
        dcc.Link(
            dbc.Button("Projects Upload →", color="dark", size="sm", className="ms-2 text-white fw-bold"),
            href="/projects-identified-admin",
        ),
    ]),
    html.Hr(),
    dcc.Interval(id="vcadmin-refresh-interval", interval=10_000, n_intervals=0),
    html.Div(id="vcadmin-list-container"),
], fluid=True)


# ─── Render pending list ───────────────────────────────────────
@dash.callback(
    Output("vcadmin-list-container", "children"),
    Input("vcadmin-refresh-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def vcadmin_refresh_pending(_, zone, dept):
    if not zone or not dept:
        return dash.no_update
        
    rows = _read_vc_pending(zone, dept)
    if not rows:
        return dbc.Alert("No pending Value Credited approvals 🎉", color="info")
    return [_build_card(r) for r in rows]


# ─── Approve ───────────────────────────────────────────────────
@dash.callback(
    Output({"type": "vcadmin-result", "uid": MATCH}, "children"),
    Input({"type": "vcadmin-approve-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def vcadmin_approve(_):
    uid = ctx.triggered_id["uid"]
    
    if not os.path.isfile(VC_PENDING_CSV):
        return dbc.Alert("Pending queue missing", color="danger")
        
    with open(VC_PENDING_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found in queue", color="warning")

    zone = target["zone"]
    dept = target["dept"]
    action = target.get("action", "add")
    
    folder = os.path.join(BASE_PATH, zone, dept)
    os.makedirs(folder, exist_ok=True)
    file_path = os.path.join(folder, "value.csv")

    try:
        new_row = pd.DataFrame([{
            "Date": target.get("date", ""),
            "Item Name": target.get("item_name", ""),
            "Tonnage": float(target.get("tonnage", 0))
        }])

        if action == "add":
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                df = pd.concat([new_row, df], ignore_index=True)
            else:
                df = new_row
            df.to_csv(file_path, index=False)
            
        elif action == "delete":
            if os.path.exists(file_path):
                df = pd.read_csv(file_path)
                # Filter out the exact matching row
                # We format inputs for loose matching (Date, Item Name, Tonnage bounds)
                t_date = target.get("date", "")
                t_item = target.get("item_name", "")
                t_tonnage = float(target.get("tonnage", 0))
                
                mask = ~((df["Date"] == t_date) & 
                         (df["Item Name"] == t_item) & 
                         ((df["Tonnage"] - t_tonnage).abs() < 0.01))
                
                df = df[mask]
                df.to_csv(file_path, index=False)
                
    except Exception as e:
        return dbc.Alert(f"File modification error: {str(e)}", color="danger")

    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "approved"
    _write_vc_pending(all_rows)

    return dbc.Alert("Approved ✔", color="success", className="mt-2 py-1")


# ─── Reject ────────────────────────────────────────────────────
@dash.callback(
    Output({"type": "vcadmin-result", "uid": MATCH}, "children", allow_duplicate=True),
    Input({"type": "vcadmin-reject-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def vcadmin_reject(_):
    uid = ctx.triggered_id["uid"]
    
    if not os.path.isfile(VC_PENDING_CSV):
        return dash.no_update
        
    with open(VC_PENDING_CSV, newline="", encoding="utf-8") as f:
        all_rows = list(csv.DictReader(f))

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found in queue", color="warning")

    # Remove from CSV entirely or mark rejected
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "rejected"
            
    _write_vc_pending(all_rows)

    return dbc.Alert("Rejected ✘", color="danger", className="mt-2 py-1")
