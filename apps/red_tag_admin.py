import os
import shutil
import base64

import dash
from dash import html, dcc, Input, Output, State, ctx, MATCH
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from apps.red_tag_museum import (
    RED_TAG_PENDING_CSV, RED_TAG_COLUMNS,
    read_rt_pending_csv, write_rt_pending_csv,
    get_red_folder, get_red_pending_folder,
    IMG_STYLE, IMG_FRAME,
)


def _img_to_uri(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


def _pending_rows(zone=None, dept=None):
    rows = [r for r in read_rt_pending_csv() if r.get("status") == "pending"]
    if zone:
        rows = [r for r in rows if r.get("zone") == zone]
    if dept:
        rows = [r for r in rows if r.get("dept") == dept]
    return rows


def _build_card(row):
    uid = row["id"]
    zone = row["zone"]
    dept = row["dept"]
    pending_folder = get_red_pending_folder(zone, dept)

    item_path = os.path.join(pending_folder, row.get("item_file", ""))
    spec_path = os.path.join(pending_folder, row.get("spec_file", ""))

    item_img = html.Div(
        html.Img(src=_img_to_uri(item_path), style=IMG_STYLE)
        if os.path.isfile(item_path) else "No image",
        style=IMG_FRAME,
    )

    spec_img = html.Div(
        html.Img(src=_img_to_uri(spec_path), style=IMG_STYLE)
        if os.path.isfile(spec_path) else "No image",
        style=IMG_FRAME,
    )

    ti = str(row.get("total_items", ""))
    te = str(row.get("total_evaluation", ""))
    iv = ""
    try:
        if ti and te:
            iv = f"{float(te) / float(ti):g}"
    except (ValueError, TypeError, ZeroDivisionError):
        pass

    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("Item Image", className="fw-bold text-muted"),
                    item_img,
                ], md=4),
                dbc.Col([
                    html.Small("Specification Image", className="fw-bold text-muted"),
                    spec_img,
                ], md=4),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Span("Zone: ", className="fw-bold"),
                            html.Span(zone),
                        ]),
                        html.Div([
                            html.Span("Dept: ", className="fw-bold"),
                            html.Span(dept),
                        ]),
                        html.Div([
                            html.Span("Total Items: ", className="fw-bold"),
                            html.Span(ti),
                        ]),
                        html.Div([
                            html.Span("Item Value: ", className="fw-bold"),
                            html.Span(iv),
                        ]) if iv else html.Div(),
                        html.Div([
                            html.Span("Total Evaluation: ", className="fw-bold"),
                            html.Span(te),
                        ]),
                        html.Div([
                            html.Span("Contact Phone: ", className="fw-bold"),
                            (
                                html.A(
                                    row.get("contact_phone", ""),
                                    href=f"tel:{row.get('contact_phone', '')}",
                                    className="text-danger fw-semibold text-decoration-none",
                                )
                                if row.get("contact_phone") else
                                html.Span(
                                    "⚠ Not provided (legacy upload)",
                                    className="badge bg-warning text-dark",
                                    style={"fontSize": "11px"},
                                )
                            ),
                        ]),
                        html.Div([
                            html.Span("Submitted: ", className="fw-bold"),
                            html.Span(row.get("submitted_at", "")),
                        ], className="text-muted small mt-1"),

                        html.Div([
                            dbc.Button(
                                "✔ Approve",
                                id={"type": "rtadmin-approve-btn", "uid": uid},
                                color="success",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "✘ Reject",
                                id={"type": "rtadmin-reject-btn", "uid": uid},
                                color="danger",
                                size="sm",
                            ),
                        ], className="mt-3"),
                    ]),
                ], md=4),
            ]),
            html.Div(id={"type": "rtadmin-result", "uid": uid}),
        ]),
        className="mb-3 shadow-sm",
    )


layout = dbc.Container([
    html.H4("Red Tag Museum — Approvals", className="mt-3 mb-3 text-danger"),
    html.Div([
        dcc.Link(
            dbc.Button("← Progress Approvals", color="primary", size="sm"),
            href="/progress-admin",
        ),
        dcc.Link(
            dbc.Button("Greenery Approvals →", color="success", size="sm", className="ms-2"),
            href="/greenery-admin",
        ),
        dcc.Link(
            dbc.Button("Value Credited Approvals →", color="info", size="sm", className="ms-2 text-white fw-bold"),
            href="/value-credited-admin",
        ),
        dcc.Link(
            dbc.Button("Projects Upload →", color="dark", size="sm", className="ms-2 text-white fw-bold"),
            href="/projects-identified-admin",
        ),
    ]),
    html.Hr(),
    dcc.Interval(id="rtadmin-refresh-interval", interval=10_000, n_intervals=0),
    html.Div(id="rtadmin-list-container"),
], fluid=True)


# ─── Render pending list ───────────────────────────────────────
@dash.callback(
    Output("rtadmin-list-container", "children"),
    Input("rtadmin-refresh-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def rtadmin_refresh_pending(_, zone, dept):
    if not zone or not dept:
        return dash.no_update
        
    rows = _pending_rows(zone, dept)
    if not rows:
        return dbc.Alert("No pending Red Tag approvals 🎉", color="info")
    return [_build_card(r) for r in rows]


# ─── Approve ───────────────────────────────────────────────────
@dash.callback(
    Output({"type": "rtadmin-result", "uid": MATCH}, "children"),
    Input({"type": "rtadmin-approve-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def rtadmin_approve(_):
    uid = ctx.triggered_id["uid"]
    all_rows = read_rt_pending_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found", color="warning")

    zone = target["zone"]
    dept = target["dept"]
    pending_folder = get_red_pending_folder(zone, dept)
    main_folder = get_red_folder(zone, dept)

    # Move item image
    src_item = os.path.join(pending_folder, target.get("item_file", ""))
    dst_item = os.path.join(main_folder, target.get("item_file", ""))
    if os.path.isfile(src_item):
        shutil.move(src_item, dst_item)

    # Move spec image
    src_spec = os.path.join(pending_folder, target.get("spec_file", ""))
    dst_spec = os.path.join(main_folder, target.get("spec_file", ""))
    if os.path.isfile(src_spec):
        shutil.move(src_spec, dst_spec)

    # Update CSV status
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "approved"
    write_rt_pending_csv(all_rows)

    return dbc.Alert("Approved ✔ — Item now visible in gallery", color="success", className="mt-2 py-1")


# ─── Reject ────────────────────────────────────────────────────
@dash.callback(
    Output({"type": "rtadmin-result", "uid": MATCH}, "children", allow_duplicate=True),
    Input({"type": "rtadmin-reject-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def rtadmin_reject(_):
    uid = ctx.triggered_id["uid"]
    all_rows = read_rt_pending_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found", color="warning")

    zone = target["zone"]
    dept = target["dept"]
    pending_folder = get_red_pending_folder(zone, dept)

    # Delete item image
    src_item = os.path.join(pending_folder, target.get("item_file", ""))
    if os.path.isfile(src_item):
        os.remove(src_item)

    # Delete spec image
    src_spec = os.path.join(pending_folder, target.get("spec_file", ""))
    if os.path.isfile(src_spec):
        os.remove(src_spec)

    # Remove from CSV entirely
    all_rows = [r for r in all_rows if r["id"] != uid]
    write_rt_pending_csv(all_rows)

    return dbc.Alert("Rejected & Deleted ✘", color="danger", className="mt-2 py-1")
