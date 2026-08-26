import os
import shutil
import csv
import base64

import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH, callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from datetime import datetime

from apps.greenery import (
    GREENERY_PENDING_CSV, GREENERY_PENDING_COLUMNS, BASE_PATH,
    read_greenery_pending_csv, write_greenery_pending_csv,
    get_greenery_folder, get_pending_folder,
    save_text, save_area_code, IMG_STYLE, IMG_FRAME_STYLE,
)


def _img_to_uri(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


def _pending_rows(zone=None, dept=None):
    rows = [r for r in read_greenery_pending_csv() if r.get("status") == "pending"]
    if zone:
        rows = [r for r in rows if r.get("zone") == zone]
    if dept:
        rows = [r for r in rows if r.get("dept") == dept]
    return rows


def _build_card(row):
    uid = row["id"]
    zone = row["zone"]
    dept = row["dept"]
    pending_folder = get_pending_folder(zone, dept)
    main_folder = get_greenery_folder(zone, dept)

    location_name = row.get("location_name", "")
    sub_location_name = row.get("sub_location_name", "")
    responsible_person = row.get("responsible_person", "")
    area_code = str(row.get("area_code", ""))

    if not location_name or not responsible_person or not area_code:
        from apps.greenery import load_text_map
        text_map = load_text_map(zone, dept)
        t_data = text_map.get(row.get("before_file", ""), {})
        
        if not location_name:
            location_name = t_data.get("text", "")
        if not responsible_person:
            responsible_person = t_data.get("text2", "")
        if not area_code or area_code == "None":
            area_code = str(t_data.get("area_code", ""))

    if area_code and area_code != "None":
        try:
            ac_val = int(area_code)
            from apps.area_master_admin import read_area_master_for
            master_data = read_area_master_for(zone, dept)
            rec = master_data.get(ac_val, {})
            
            if not location_name:
                location_name = rec.get("location_name", "")
            if not sub_location_name:
                sub_location_name = rec.get("sub_location_name", "")
            if not responsible_person:
                responsible_person = rec.get("responsible_person", "")
                
            if ac_val == 0:
                from apps.area_master_admin import get_exec_team_person
                if not location_name:
                    location_name = dept
                if not sub_location_name:
                    sub_location_name = dept
                if not responsible_person:
                    responsible_person = get_exec_team_person(zone, dept)
        except Exception:
            pass

    # before_file may already be in the main folder if this is an after-only submission
    before_path = os.path.join(pending_folder, row["before_file"])
    if not os.path.isfile(before_path):
        before_path = os.path.join(main_folder, row["before_file"])

    after_path = os.path.join(pending_folder, row["after_file"]) if row.get("after_file") else ""

    before_img = html.Div(
        html.Img(src=_img_to_uri(before_path), style=IMG_STYLE) if os.path.isfile(before_path) else "No image",
        style=IMG_FRAME_STYLE,
    )

    if after_path and os.path.isfile(after_path):
        after_img = html.Div(
            html.Img(src=_img_to_uri(after_path), style=IMG_STYLE),
            style=IMG_FRAME_STYLE,
        )
    else:
        after_img = html.Div(
            "No after image",
            style={**IMG_FRAME_STYLE, "color": "#888", "fontSize": "14px"},
        )

    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small("Before", className="fw-bold text-muted"),
                    before_img,
                ], md=4),
                dbc.Col([
                    html.Small("After", className="fw-bold text-muted"),
                    after_img,
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
                            html.Span("Location: ", className="fw-bold"),
                            html.Span(location_name),
                        ]),
                        html.Div([
                            html.Span("Sub Location: ", className="fw-bold"),
                            html.Span(sub_location_name),
                        ]),
                        html.Div([
                            html.Span("Person: ", className="fw-bold"),
                            html.Span(responsible_person),
                        ]),
                        html.Div([
                            html.Span("Area Code: ", className="fw-bold"),
                            html.Span(area_code),
                        ]),
                        html.Div([
                            html.Span("Submitted: ", className="fw-bold"),
                            html.Span(row.get("submitted_at", "")),
                        ], className="text-muted small mt-1"),

                        html.Div([
                            dbc.Button(
                                "✔ Approve",
                                id={"type": "gadmin-approve-btn", "uid": uid},
                                color="success",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "✘ Reject",
                                id={"type": "gadmin-reject-btn", "uid": uid},
                                color="danger",
                                size="sm",
                            ),
                        ], className="mt-3"),
                    ]),
                ], md=4),
            ]),
            html.Div(id={"type": "gadmin-approval-result", "uid": uid}),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Reject image"), close_button=False),
                    dbc.ModalBody(
                        [
                            html.Label("Rejection remark", className="fw-bold"),
                            dbc.Textarea(
                                id={"type": "gadmin-reject-remark-input", "uid": uid},
                                placeholder="Enter why this Greenery image is being rejected",
                                rows=4,
                            ),
                            html.Div(
                                id={"type": "gadmin-reject-remark-error", "uid": uid},
                                className="text-danger small mt-2",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id={"type": "gadmin-reject-cancel-btn", "uid": uid},
                                color="secondary",
                                outline=True,
                                className="me-2",
                            ),
                            dbc.Button(
                                "Reject",
                                id={"type": "gadmin-reject-confirm-btn", "uid": uid},
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id={"type": "gadmin-reject-remark-modal", "uid": uid},
                is_open=False,
                backdrop="static",
                keyboard=False,
            ),
        ]),
        className="mb-3 shadow-sm",
    )


layout = dbc.Container([
    html.H4("Greenery Upload Approvals", className="mt-3 mb-3"),
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
            dbc.Button("Value Credited Approvals →", color="info", size="sm", className="ms-2 text-white fw-bold"),
            href="/value-credited-admin",
        ),
        dcc.Link(
            dbc.Button("Projects Upload →", color="dark", size="sm", className="ms-2 text-white fw-bold"),
            href="/projects-identified-admin",
        ),
    ]),
    html.Hr(),
    dcc.Interval(id="gadmin-refresh-interval", interval=10_000, n_intervals=0),
    html.Div(id="gadmin-list-container"),
], fluid=True)


# ─── Render pending list ───────────────────────────────────────

@dash.callback(
    Output("gadmin-list-container", "children"),
    Input("gadmin-refresh-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def gadmin_refresh_pending_list(_, zone, dept):
    if not zone or not dept:
        return dash.no_update
        
    rows = _pending_rows(zone, dept)
    if not rows:
        return dbc.Alert("No pending approvals 🎉", color="info")
    return [_build_card(r) for r in rows]


# ─── Approve ───────────────────────────────────────────────────

@dash.callback(
    Output({"type": "gadmin-approval-result", "uid": MATCH}, "children"),
    Input({"type": "gadmin-approve-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def gadmin_approve_upload(_):
    uid = ctx.triggered_id["uid"]
    all_rows = read_greenery_pending_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found", color="warning")

    zone = target["zone"]
    dept = target["dept"]
    pending_folder = get_pending_folder(zone, dept)
    main_folder = get_greenery_folder(zone, dept)

    # Move before image
    src_before = os.path.join(pending_folder, target["before_file"])
    dst_before = os.path.join(main_folder, target["before_file"])
    if os.path.isfile(src_before):
        shutil.move(src_before, dst_before)

    # Move after image
    if target.get("after_file"):
        src_after = os.path.join(pending_folder, target["after_file"])
        dst_after = os.path.join(main_folder, target["after_file"])
        if os.path.isfile(src_after):
            shutil.move(src_after, dst_after)

    # Save text metadata to the progress text.csv (skip for after-only submissions)
    if target.get("location_name", "").strip():
        save_text(
            zone, dept,
            target["before_file"],
            target.get("location_name", ""),
            target.get("responsible_person", ""),
        )

        # Save area code metadata
        area_code = target.get("area_code", "")
        if area_code:
            save_area_code(zone, dept, target["before_file"], area_code)

    # Update CSV status
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "approved"
    write_greenery_pending_csv(all_rows)

    return dbc.Alert("Approved ✔", color="success", className="mt-2 py-1")


# ─── Reject ────────────────────────────────────────────────────

@dash.callback(
    Output({"type": "gadmin-approval-result", "uid": MATCH}, "children", allow_duplicate=True),
    Output({"type": "gadmin-reject-remark-modal", "uid": MATCH}, "is_open"),
    Output({"type": "gadmin-reject-remark-input", "uid": MATCH}, "value"),
    Output({"type": "gadmin-reject-remark-error", "uid": MATCH}, "children"),
    Input({"type": "gadmin-reject-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "gadmin-reject-cancel-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "gadmin-reject-confirm-btn", "uid": MATCH}, "n_clicks"),
    State({"type": "gadmin-reject-remark-input", "uid": MATCH}, "value"),
    prevent_initial_call=True,
)
def gadmin_handle_reject_with_remark(_open_clicks, _cancel_clicks, _confirm_clicks, remark):
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate

    action = triggered["type"]
    uid = triggered["uid"]

    if action == "gadmin-reject-btn":
        return dash.no_update, True, "", ""

    if action == "gadmin-reject-cancel-btn":
        return dash.no_update, False, "", ""

    remark = (remark or "").strip()
    if not remark:
        return dash.no_update, True, dash.no_update, "Remark is required before rejecting this image."

    all_rows = read_greenery_pending_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found", color="warning"), False, "", ""

    zone = target["zone"]
    dept = target["dept"]
    rejected_at = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    # Update CSV status
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "rejected"
            r["rejection_remark"] = remark
            r["rejected_at"] = rejected_at
    write_greenery_pending_csv(all_rows)

    return dbc.Alert("Rejected with remark. Image will be kept for 24 days.", color="danger", className="mt-2 py-1"), False, "", ""


@dash.callback(
    Output("gadmin-refresh-interval", "disabled"),
    Input({"type": "gadmin-reject-remark-modal", "uid": ALL}, "is_open"),
)
def gadmin_disable_refresh_while_reject_modal_open(open_states):
    return any(bool(open_state) for open_state in (open_states or []))
