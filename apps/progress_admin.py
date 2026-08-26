import os
import shutil
import csv
import base64
import time
import io
from PIL import Image
import urllib.parse

import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH, callback
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate
from datetime import datetime

from apps.progress import (
    PENDING_CSV, PENDING_COLUMNS, BASE_PATH,
    read_pending_csv, write_pending_csv,
    get_progress_folder, get_pending_folder,
    save_text, save_area_code, IMG_STYLE, IMG_FRAME_STYLE,
)


def _img_to_uri(path):
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


def _pending_rows(zone=None, dept=None):
    rows = [r for r in read_pending_csv() if r.get("status") == "pending"]
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
    main_folder = get_progress_folder(zone, dept)

    location_name = row.get("location_name", "")
    sub_location_name = row.get("sub_location_name", "")
    responsible_person = row.get("responsible_person", "")
    area_code = str(row.get("area_code", ""))

    if not location_name or not responsible_person or not area_code:
        from apps.progress import load_text_map
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
                                id={"type": "padmin-approve-btn", "uid": uid},
                                color="success",
                                size="sm",
                                className="me-2",
                            ),
                            dbc.Button(
                                "✘ Reject",
                                id={"type": "padmin-reject-btn", "uid": uid},
                                color="danger",
                                size="sm",
                            ),
                        ], className="mt-3"),
                    ]),
                ], md=4),
            ]),
            html.Div(id={"type": "padmin-approval-result", "uid": uid}),
            dbc.Modal(
                [
                    dbc.ModalHeader(dbc.ModalTitle("Reject image"), close_button=False),
                    dbc.ModalBody(
                        [
                            html.Label("Rejection remark", className="fw-bold"),
                            dbc.Textarea(
                                id={"type": "padmin-reject-remark-input", "uid": uid},
                                placeholder="Enter why this Progress image is being rejected",
                                rows=4,
                            ),
                            html.Div(
                                id={"type": "padmin-reject-remark-error", "uid": uid},
                                className="text-danger small mt-2",
                            ),
                        ]
                    ),
                    dbc.ModalFooter(
                        [
                            dbc.Button(
                                "Cancel",
                                id={"type": "padmin-reject-cancel-btn", "uid": uid},
                                color="secondary",
                                outline=True,
                                className="me-2",
                            ),
                            dbc.Button(
                                "Reject",
                                id={"type": "padmin-reject-confirm-btn", "uid": uid},
                                color="danger",
                            ),
                        ]
                    ),
                ],
                id={"type": "padmin-reject-remark-modal", "uid": uid},
                is_open=False,
                backdrop="static",
                keyboard=False,
            ),
        ]),
        className="mb-3 shadow-sm",
    )


layout = dbc.Container([
    html.H4("Progress Upload Approvals", className="mt-3 mb-3"),
    html.Div([
        dcc.Link(
            dbc.Button("Manage Area Master →", color="primary", size="sm"),
            href="/area-master",
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
            dbc.Button("Value Credited Approvals →", color="info", size="sm", className="ms-2 text-white fw-bold"),
            href="/value-credited-admin",
        ),
        dcc.Link(
            dbc.Button("Projects Upload →", color="dark", size="sm", className="ms-2 text-white fw-bold"),
            href="/projects-identified-admin",
        ),
    ]),
    html.Hr(),
    dcc.Store(id="admin-layout-map-update-trigger", data=0),
    html.Div(id="admin-layout-map-section", className="mb-4"),
    html.Hr(),
    dcc.Store(id="admin-compliance-doc-update-trigger", data=0),
    html.Div(id="admin-compliance-doc-section", className="mb-4", style={"maxWidth": "900px", "margin": "0 auto"}),
    html.Hr(),
    dcc.Interval(id="padmin-refresh-interval", interval=10_000, n_intervals=0),
    html.Div(id="padmin-list-container"),
], fluid=True)


# ─── Render pending list ───────────────────────────────────────

@dash.callback(
    Output("padmin-list-container", "children"),
    Input("padmin-refresh-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def padmin_refresh_pending_list(_, zone, dept):
    if not zone or not dept:
        return dash.no_update
        
    rows = _pending_rows(zone, dept)
    if not rows:
        return dbc.Alert("No pending approvals 🎉", color="info")
    return [_build_card(r) for r in rows]


# ─── Approve ───────────────────────────────────────────────────

@dash.callback(
    Output({"type": "padmin-approval-result", "uid": MATCH}, "children"),
    Input({"type": "padmin-approve-btn", "uid": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def padmin_approve_upload(_):
    uid = ctx.triggered_id["uid"]
    all_rows = read_pending_csv()

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
    main_folder = get_progress_folder(zone, dept)

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
    write_pending_csv(all_rows)

    return dbc.Alert("Approved ✔", color="success", className="mt-2 py-1")


# ─── Reject ────────────────────────────────────────────────────

@dash.callback(
    Output({"type": "padmin-approval-result", "uid": MATCH}, "children", allow_duplicate=True),
    Output({"type": "padmin-reject-remark-modal", "uid": MATCH}, "is_open"),
    Output({"type": "padmin-reject-remark-input", "uid": MATCH}, "value"),
    Output({"type": "padmin-reject-remark-error", "uid": MATCH}, "children"),
    Input({"type": "padmin-reject-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "padmin-reject-cancel-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "padmin-reject-confirm-btn", "uid": MATCH}, "n_clicks"),
    State({"type": "padmin-reject-remark-input", "uid": MATCH}, "value"),
    prevent_initial_call=True,
)
def padmin_handle_reject_with_remark(_open_clicks, _cancel_clicks, _confirm_clicks, remark):
    triggered = ctx.triggered_id
    if not triggered:
        raise PreventUpdate

    action = triggered["type"]
    uid = triggered["uid"]

    if action == "padmin-reject-btn":
        return dash.no_update, True, "", ""

    if action == "padmin-reject-cancel-btn":
        return dash.no_update, False, "", ""

    remark = (remark or "").strip()
    if not remark:
        return dash.no_update, True, dash.no_update, "Remark is required before rejecting this image."

    all_rows = read_pending_csv()

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
    write_pending_csv(all_rows)

    return dbc.Alert("Rejected with remark. Image will be kept for 24 days.", color="danger", className="mt-2 py-1"), False, "", ""


@dash.callback(
    Output("padmin-refresh-interval", "disabled"),
    Input({"type": "padmin-reject-remark-modal", "uid": ALL}, "is_open"),
)
def padmin_disable_refresh_while_reject_modal_open(open_states):
    return any(bool(open_state) for open_state in (open_states or []))


# ─── Layout Map Upload ─────────────────────────────────────────

@dash.callback(
    Output("admin-layout-map-section", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
    Input("admin-layout-map-update-trigger", "data")
)
def admin_render_dept_map(zone, dept, _):
    if not zone or not dept:
        return html.Div()

    folder = os.path.join("./assets/K5", zone, dept)
    map_path = os.path.join(folder, "map.png")

    if os.path.isfile(map_path):
        with open(map_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_src = f"data:image/png;base64,{encoded}"

        return html.Div([
            html.H5(f"Layout Map for {dept}:", className="mb-3", style={"textAlign": "center"}),
            html.Div(
                html.Img(src=img_src, style={"maxWidth": "100%", "maxHeight": "500px", "border": "2px solid #ccc", "borderRadius": "8px"}),
                style={"marginBottom": "15px", "textAlign": "center"}
            ),
            html.Div(
                dbc.Button("Delete & Reupload Map", id="admin-layout-map-delete-btn", color="danger", size="sm"),
                style={"textAlign": "center"}
            )
        ])
    else:
        return html.Div([
            html.H5(f"Upload Layout Map for {dept}", className="mb-3 text-muted", style={"textAlign": "center"}),
            dcc.Upload(
                id="admin-layout-map-upload-cmp",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select Image File", style={"color": "#0d6efd", "fontWeight": "bold", "textDecoration": "underline"})
                ]),
                style={
                    "width": "60%",
                    "height": "80px",
                    "lineHeight": "80px",
                    "borderWidth": "2px",
                    "borderStyle": "dashed",
                    "borderRadius": "8px",
                    "textAlign": "center",
                    "margin": "0 auto",
                    "cursor": "pointer",
                    "backgroundColor": "#f8f9fa"
                },
                multiple=False
            )
        ])

@dash.callback(
    Output("admin-layout-map-update-trigger", "data", allow_duplicate=True),
    Input("admin-layout-map-upload-cmp", "contents"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True
)
def admin_handle_map_upload(contents, zone, dept):
    if not contents or not zone or not dept:
        raise dash.exceptions.PreventUpdate

    folder = os.path.join("./assets/K5", zone, dept)
    os.makedirs(folder, exist_ok=True)
    map_path = os.path.join(folder, "map.png")

    try:
        _, encoded = contents.split(",", 1)
        binary = base64.b64decode(encoded)
        img = Image.open(io.BytesIO(binary))
        if img.mode != "RGBA":
            img = img.convert("RGBA")
        img.save(map_path, format="PNG", optimize=True)
    except Exception as e:
        print("Admin Map upload error:", e)

    return time.time()

@dash.callback(
    Output("admin-layout-map-update-trigger", "data", allow_duplicate=True),
    Input("admin-layout-map-delete-btn", "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True
)
def admin_handle_map_delete(n_clicks, zone, dept):
    if not n_clicks or not zone or not dept:
        raise dash.exceptions.PreventUpdate

    map_path = os.path.join("./assets/K5", zone, dept, "map.png")
    if os.path.isfile(map_path):
        os.remove(map_path)

    return time.time()


# ─── Compliance Documents Upload ───────────────────────────────

@dash.callback(
    Output("admin-compliance-doc-section", "children"),
    Input("selected-department", "data"),
    Input("admin-compliance-doc-update-trigger", "data")
)
def admin_render_compliance_docs(dept, _):
    if not dept:
        return html.Div()
        
    safe_area = "".join(c for c in dept if c.isalnum() or c in " _-").strip()
    area_path = os.path.join("assets", "upcoming_events", safe_area)
    
    events = []
    if os.path.exists(area_path) and os.path.isdir(area_path):
        for fname in os.listdir(area_path):
            fpath = os.path.join(area_path, fname)
            if os.path.isfile(fpath):
                mtime = os.path.getmtime(fpath)
                dt = datetime.fromtimestamp(mtime)
                events.append({
                    "filename": fname,
                    "date": dt,
                    "url": f"/assets/upcoming_events/{safe_area}/{urllib.parse.quote(fname)}",
                    "path": fpath
                })
                
    events.sort(key=lambda x: x["date"], reverse=True)
    
    cards = []
    for i, ev in enumerate(events):
        idx = f"{i+1:02d}"
        title = ev["filename"].rsplit('.', 1)[0]
        if len(title) > 30:
            title = title[:30] + "..."
        date_str = ev["date"].strftime("%d %b %Y")
        
        card = html.Div(
            [
                html.A(
                    html.Div(
                        [
                            html.Div(
                                idx,
                                style={
                                    "width": "50px", "height": "50px", "backgroundColor": "#4caf50",
                                    "clipPath": "polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%)",
                                    "display": "flex", "alignItems": "center", "justifyContent": "center",
                                    "color": "white", "fontWeight": "bold", "fontSize": "18px", "marginRight": "15px",
                                    "flexShrink": "0"
                                }
                            ),
                            html.Div(
                                [
                                    html.Div(title, style={"margin": "0", "fontSize": "14px", "fontWeight": "bold", "color": "#333", "whiteSpace": "normal", "wordBreak": "break-word"}),
                                    html.Div(f"Area: {dept} | {date_str}", style={"margin": "0", "fontSize": "12px", "color": "#777", "marginTop": "4px"}),
                                ]
                            ),
                        ],
                        style={
                            "background": "white", "borderRadius": "8px", "padding": "15px", "display": "flex",
                            "alignItems": "center", "boxShadow": "0 4px 6px rgba(0,0,0,0.1)", "width": "100%", "cursor": "pointer"
                        }
                    ),
                    href=ev["url"],
                    target="_blank",
                    style={"textDecoration": "none"}
                ),
                html.Div(
                    dbc.Button("Delete Document", id={"type": "admin-compliance-doc-delete-btn", "filename": ev["filename"]}, color="danger", size="sm", className="mt-2 w-100"),
                    style={"padding": "0 10px"}
                )
            ],
            style={"minWidth": "280px", "maxWidth": "350px", "display": "flex", "flexDirection": "column"}
        )
        cards.append(card)

    docs_display = html.Div(
        [
            html.Div(
                "DOCUMENTS",
                style={
                    "writingMode": "vertical-rl", "transform": "rotate(180deg)", "fontWeight": "bold",
                    "fontSize": "13px", "letterSpacing": "2px", "color": "#334", "marginRight": "10px",
                    "paddingTop": "10px", "minHeight": "100px"
                }
            ),
            html.Div(
                cards if cards else html.Div("No documents uploaded yet.", style={"padding": "20px", "color": "#777", "fontStyle": "italic"}),
                style={"display": "flex", "gap": "15px", "overflowX": "auto", "paddingBottom": "10px", "width": "100%"}
            )
        ],
        style={
            "display": "flex", "background": "#eef2f5", "padding": "20px", "borderRadius": "10px",
            "marginBottom": "20px", "alignItems": "flex-start", "boxSizing": "border-box"
        }
    )

    upload_display = html.Div([
        html.H5(f"Upload Compliance Documents for {dept}", className="mb-3 text-muted", style={"textAlign": "center"}),
        dcc.Upload(
            id="admin-compliance-doc-upload-cmp",
            children=html.Div([
                "Drag and Drop or ",
                html.A("Select Files", style={"color": "#0d6efd", "fontWeight": "bold", "textDecoration": "underline"})
            ]),
            style={
                "width": "60%",
                "height": "80px",
                "lineHeight": "80px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "borderRadius": "8px",
                "textAlign": "center",
                "margin": "0 auto",
                "cursor": "pointer",
                "backgroundColor": "#f8f9fa"
            },
            multiple=True
        ),
        html.Div(id="admin-compliance-doc-upload-msg", style={"textAlign": "center", "marginTop": "10px", "color": "green"})
    ])

    return html.Div([docs_display, upload_display])

@dash.callback(
    Output("admin-compliance-doc-update-trigger", "data", allow_duplicate=True),
    Output("admin-compliance-doc-upload-msg", "children"),
    Input("admin-compliance-doc-upload-cmp", "contents"),
    State("admin-compliance-doc-upload-cmp", "filename"),
    State("selected-department", "data"),
    prevent_initial_call=True
)
def admin_handle_compliance_doc_upload(list_of_contents, list_of_names, dept):
    if not list_of_contents or not dept:
        raise dash.exceptions.PreventUpdate

    safe_area = "".join(c for c in dept if c.isalnum() or c in " _-").strip()
    folder = os.path.join("assets", "upcoming_events", safe_area)
    os.makedirs(folder, exist_ok=True)

    success_count = 0
    error_msgs = []
    for content, name in zip(list_of_contents, list_of_names):
        try:
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)

            size_mb = len(decoded) / (1024 * 1024)
            if size_mb > 20:
                error_msgs.append(f"The file {name} being uploaded is bigger than 20 mb. Please use upload file of size less than 20 mb.")
                continue

            if '.' not in name:
                name += '.pdf'

            if 10 < size_mb <= 20:
                ext = name.split('.')[-1].lower()
                if ext in ['jpg', 'jpeg', 'png', 'gif']:
                    try:
                        import io
                        from PIL import Image
                        img = Image.open(io.BytesIO(decoded))
                        if img.mode != 'RGB':
                            img = img.convert('RGB')
                        img.thumbnail((1600, 1600))
                        buf = io.BytesIO()
                        img.save(buf, format="JPEG", quality=70)
                        decoded = buf.getvalue()
                        name = name.rsplit('.', 1)[0] + '.jpg'
                    except Exception as e:
                        print("Admin image compression error:", e)

            file_path = os.path.join(folder, name)
            with open(file_path, "wb") as f:
                f.write(decoded)
            success_count += 1
        except Exception as e:
            print(f"Compliance Doc upload error for {name}:", e)

    if error_msgs:
        msg = html.Div([
            html.Div(f"Successfully uploaded {success_count} format(s)." if success_count > 0 else ""),
            html.Div(" | ".join(error_msgs), style={"color": "red", "marginTop": "5px"})
        ])
    else:
        msg = html.Div(f"Successfully uploaded {success_count} format(s)." if success_count > 0 else "Upload failed.", style={"color": "green", "marginTop": "5px"})
        
    return time.time(), msg

@dash.callback(
    Output("admin-compliance-doc-update-trigger", "data", allow_duplicate=True),
    Input({"type": "admin-compliance-doc-delete-btn", "filename": ALL}, "n_clicks"),
    State("selected-department", "data"),
    prevent_initial_call=True
)
def admin_handle_compliance_doc_delete(n_clicks_list, dept):
    if not any(n_clicks_list) or not dept:
        raise dash.exceptions.PreventUpdate

    triggered_id = ctx.triggered_id
    filename = triggered_id["filename"]

    safe_area = "".join(c for c in dept if c.isalnum() or c in " _-").strip()
    file_path = os.path.join("assets", "upcoming_events", safe_area, filename)
    
    if os.path.isfile(file_path):
        os.remove(file_path)

    return time.time()
