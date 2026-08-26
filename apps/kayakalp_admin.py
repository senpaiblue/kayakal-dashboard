"""
Kayakalp Credential Management — Admin Module
================================================
Allows the upload-side admin to create / update username & password
for each of the 35 Execution Team members.  Credentials are persisted
in Data/execution_team.csv (columns: Username, Password).

Tab 2: Image Deletion Requests — approve/reject deletion requests
submitted from the Progress and Greenery pages.

All Dash component IDs are prefixed with "kyk-" to avoid collisions.
Deletion-request IDs use the "kyk-del-" prefix.
"""

import os
import csv
import pandas as pd
import dash
from dash import html, dcc, Input, Output, State, ALL, MATCH, ctx, no_update, callback
import dash_bootstrap_components as dbc
from datetime import datetime
import base64
import urllib.parse
from app import app

from apps.progress import (
    PROGRESS_DEL_CSV, PROGRESS_DEL_COLUMNS, BASE_PATH,
    read_progress_del_csv, write_progress_del_csv,
    get_progress_folder,
)
from apps.greenery import (
    GREENERY_DEL_CSV, GREENERY_DEL_COLUMNS,
    read_greenery_del_csv, write_greenery_del_csv,
    get_greenery_folder,
)
from apps.red_tag_museum import (
    RED_TAG_DEL_CSV, RED_TAG_DEL_COLUMNS,
    read_rt_del_csv, write_rt_del_csv,
    get_red_folder, read_rt_pending_csv, write_rt_pending_csv
)
from apps.kayakalp_ac0_settings import (
    read_kayakalp_ac0_delete_allowed,
    write_kayakalp_ac0_delete_allowed,
)

# ── paths ──────────────────────────────────────────────
CSV_PATH = os.path.join("Data", "execution_team.csv")
EVENTS_DIR = os.path.join("assets", "upcoming_events")
os.makedirs(EVENTS_DIR, exist_ok=True)


# ── helpers ────────────────────────────────────────────
def _read_team():
    """Read execution_team.csv and return list of dicts."""
    df = pd.read_csv(CSV_PATH, keep_default_na=False)
    # Ensure Username / Password columns exist
    for col in ("Username", "Password"):
        if col not in df.columns:
            df[col] = ""
    return df.to_dict("records")


def _save_team(records):
    """Write list of dicts back to execution_team.csv."""
    df = pd.DataFrame(records)
    df.to_csv(CSV_PATH, index=False)


def _img_to_uri_kyk(path):
    """Convert image file to data-URI for inline display."""
    if not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


# ── layout builder (called fresh on every page load) ──
def _build_table(records):
    """Return a Bootstrap-styled table of all 35 rows."""
    header = dbc.Row(
        [
            dbc.Col(html.B("S NO"), width=1),
            dbc.Col(html.B("Area"), width=2),
            dbc.Col(html.B("Execution Team"), width=2),
            dbc.Col(html.B("Username"), width=2),
            dbc.Col(html.B("Password"), width=2),
            dbc.Col(html.B("Events / Files"), width=2),
            dbc.Col(html.B(""), width=1),
        ],
        className="py-2 bg-light border-bottom fw-bold",
    )

    rows = [header]
    for r in records:
        sno = r["S NO"]
        safe_area = "".join(c for c in r["Area"] if c.isalnum() or c in " _-").strip()
        area_dir = os.path.join(EVENTS_DIR, safe_area)
        
        file_list_ui = []
        if os.path.exists(area_dir):
            for fname in os.listdir(area_dir):
                fpath = os.path.join(area_dir, fname)
                if os.path.isfile(fpath):
                    file_list_ui.append(
                        html.Div(
                            [
                                html.A(fname, href=f"/assets/upcoming_events/{safe_area}/{urllib.parse.quote(fname)}", target="_blank", className="text-decoration-none small", style={"maxWidth": "120px", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "display": "inline-block"}),
                                html.Button(
                                    "X",
                                    id={"type": "kyk-del-event", "sno": sno, "filename": fname},
                                    className="btn btn-sm btn-danger ms-2 py-0 px-1",
                                    style={"fontSize": "10px", "lineHeight": "1"}
                                )
                            ],
                            className="d-flex align-items-center justify-content-between mb-1"
                        )
                    )

        rows.append(
            dbc.Row(
                [
                    dbc.Col(str(sno), width=1, className="pt-2"),
                    dbc.Col(r["Area"], width=2, className="pt-2"),
                    dbc.Col(r["Execution Team"], width=2, className="pt-2"),
                    dbc.Col(
                        dbc.Input(
                            id={"type": "kyk-user-input", "sno": sno},
                            value=r.get("Username", ""),
                            placeholder="Username",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Input(
                            id={"type": "kyk-pass-input", "sno": sno},
                            value=r.get("Password", ""),
                            placeholder="Password",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        html.Div([
                            dcc.Upload(
                                id={"type": "kyk-event-upload", "sno": sno},
                                children=html.Div("Upload", className="btn btn-sm btn-outline-secondary w-100 mb-1"),
                                multiple=True,
                                accept=".pdf,.ppt,.pptx",
                            ),
                            html.Div(file_list_ui, id={"type": "kyk-upload-status", "sno": sno}, className="mt-1")
                        ]),
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Save",
                            id={"type": "kyk-save-btn", "sno": sno},
                            color="primary",
                            size="sm",
                            n_clicks=0,
                        ),
                        width=1,
                    ),
                ],
                className="py-1 border-bottom align-items-center",
            )
        )
    return rows


# ── deletion request card builder ─────────────────────
IMG_FRAME_KYK = {
    "width": "100%",
    "height": "200px",
    "backgroundColor": "#111",
    "border": "1px solid #ccc",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "hidden",
}
IMG_STYLE_KYK = {
    "maxWidth": "100%",
    "maxHeight": "100%",
    "objectFit": "contain",
}


def _lookup_area_code_for_del_row(row, source):
    """Return area_code string from area_code.csv for this deletion request row."""
    zone = row.get("zone", "")
    dept = row.get("dept", "")
    image_file = row.get("image_file", "")
    before_file = row.get("before_file", "")
    if source == "progress":
        folder = get_progress_folder(zone, dept) if zone and dept else ""
    elif source == "greenery":
        folder = get_greenery_folder(zone, dept) if zone and dept else ""
    else:
        return ""

    area_code_val = ""
    if folder:
        area_csv_path = os.path.join(folder, "area_code.csv")
        lookup_name = before_file or image_file
        if os.path.isfile(area_csv_path) and lookup_name:
            try:
                with open(area_csv_path, newline="", encoding="utf-8") as f:
                    for ac_row in csv.DictReader(f):
                        if ac_row.get("image_name") == lookup_name:
                            area_code_val = ac_row.get("area_code", "")
                            break
            except Exception:
                pass
    return area_code_val


def _build_del_card(row, source, allow_area_zero_delete=False):
    """Build a card for one deletion request.
    source is 'progress' or 'greenery'.
    If allow_area_zero_delete is False, Area Code 0 requests show as blocked
    (unless the admin enables the switch on this page).
    """
    uid = row["id"]
    zone = row.get("zone", "")
    dept = row.get("dept", "")
    image_type = row.get("image_type", "")
    image_file = row.get("image_file", "")

    if source == "progress":
        folder = get_progress_folder(zone, dept) if zone and dept else ""
    elif source == "greenery":
        folder = get_greenery_folder(zone, dept) if zone and dept else ""
    else:
        folder = get_red_folder(zone, dept) if zone and dept else ""

    img_path = os.path.join(folder, image_file) if folder else ""
    if source == "red_tag":
        img_path = os.path.join(folder, row.get("item_file", "")) if folder else ""

    area_code_val = _lookup_area_code_for_del_row(row, source)

    # Area code 0: deletion blocked unless admin switch is on
    is_area_code_zero = str(area_code_val).strip() == "0"

    img_ui = html.Div(
        html.Img(src=_img_to_uri_kyk(img_path), style=IMG_STYLE_KYK)
        if img_path and os.path.isfile(img_path) else "Image not found",
        style=IMG_FRAME_KYK,
    )

    badge_color = "primary" if image_type == "before" else "info"

    # Build action buttons or "not allowed" message
    if is_area_code_zero and not allow_area_zero_delete:
        action_section = html.Div([
            dbc.Alert(
                "Area Code 0 — deletion not allowed (turn on the switch above to allow)",
                color="warning",
                className="py-1 px-2 mb-0",
            ),
        ], className="mt-3")
    else:
        action_section = html.Div([
            dbc.Button(
                "✔ Approve Deletion",
                id={"type": "kyk-del-approve-btn", "uid": uid, "source": source},
                color="success",
                size="sm",
                className="me-2",
            ),
            dbc.Button(
                "✘ Reject",
                id={"type": "kyk-del-reject-btn", "uid": uid, "source": source},
                color="danger",
                size="sm",
            ),
        ], className="mt-3")

    return dbc.Card(
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Small(f"{source.title()} — {image_type.title()} Image", className="fw-bold text-muted"),
                    img_ui,
                ], md=5),
                dbc.Col([
                    html.Div([
                        html.Div([
                            html.Span("Source: ", className="fw-bold"),
                            dbc.Badge(source.title(), color="secondary", className="ms-1"),
                        ]),
                        html.Div([
                            html.Span("Type: ", className="fw-bold"),
                            dbc.Badge(image_type.title(), color=badge_color, className="ms-1"),
                        ], className="mt-1"),
                        html.Div([
                            html.Span("Zone: ", className="fw-bold"),
                            html.Span(zone),
                        ], className="mt-1"),
                        html.Div([
                            html.Span("Dept: ", className="fw-bold"),
                            html.Span(dept),
                        ]),
                        html.Div([
                            html.Span("Area Code: ", className="fw-bold"),
                            html.Span(str(area_code_val) if area_code_val != "" else "N/A"),
                        ]),
                        html.Div([
                            html.Span("File: ", className="fw-bold"),
                            html.Span(image_file or row.get("item_file", ""), className="text-break"),
                        ]),
                        html.Div([
                            html.Span("Submitted: ", className="fw-bold"),
                            html.Span(row.get("submitted_at", "")),
                        ], className="text-muted small mt-1"),

                        action_section,
                    ]),
                ], md=7),
            ]),
            html.Div(id={"type": "kyk-del-result", "uid": uid, "source": source}),
        ]),
        className="mb-3 shadow-sm",
    )


# ── public layout property (re-read CSV each time) ────
def _layout():
    records = _read_team()

    # Tab 1: Credentials (existing)
    tab_credentials = dbc.Tab(
        label="Credentials",
        tab_id="kyk-tab-credentials",
        children=dbc.Container(
            [
                html.H4(
                    "Kayakalp — Execution Team Credentials",
                    className="text-center my-3",
                ),
                html.P(
                    "Set username & password for each Execution Team member. "
                    "These credentials are used on the Kayakalp 5S admin login.",
                    className="text-muted text-center mb-3",
                ),
                html.Div(id="kyk-table-wrapper", children=_build_table(records)),
                html.Div(id="kyk-save-result", className="text-center mt-3"),
            ],
            fluid=True,
        ),
    )

    # Tab 2: Image Deletion Requests (new)
    tab_deletion = dbc.Tab(
        label="Image Deletion Requests",
        tab_id="kyk-tab-deletion",
        children=dbc.Container(
            [
                html.H4(
                    "Image Deletion Requests",
                    className="text-center my-3 text-danger",
                ),
                html.P(
                    "Review and approve/reject image deletion requests from "
                    "the Progress and Greenery pages.",
                    className="text-muted text-center mb-3",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div(
                                    [
                                        html.Span(
                                            "Area Code 0 images: ",
                                            className="fw-bold me-2",
                                        ),
                                        dbc.Switch(
                                            id="kyk-del-ac0-allow-switch",
                                            value=read_kayakalp_ac0_delete_allowed(),
                                            label="Allow deletion",
                                            className="d-inline-block align-middle",
                                        ),
                                        html.Small(
                                            " Off = cannot approve; On = approve/reject allowed.",
                                            className="text-muted ms-2 d-block d-md-inline",
                                        ),
                                    ],
                                    className="text-center mb-3",
                                ),
                            ],
                            width=12,
                        ),
                    ]
                ),
                dcc.Interval(id="kyk-del-refresh-interval", interval=10_000, n_intervals=0),
                html.Div(id="kyk-del-list-container"),
            ],
            fluid=True,
        ),
    )

    return dbc.Container(
        [
            dbc.Tabs(
                [tab_credentials, tab_deletion],
                id="kyk-admin-tabs",
                active_tab="kyk-tab-credentials",
                className="mt-3",
            ),
        ],
        fluid=True,
        className="mt-3",
    )


layout = _layout


# ══════════════════════════════════════════════════════════
# CALLBACKS — Tab 1: Credentials (unchanged)
# ══════════════════════════════════════════════════════════

@app.callback(
    Output("kyk-save-result", "children"),
    Input({"type": "kyk-save-btn", "sno": ALL}, "n_clicks"),
    State({"type": "kyk-user-input", "sno": ALL}, "value"),
    State({"type": "kyk-pass-input", "sno": ALL}, "value"),
    prevent_initial_call=True,
)
def kyk_save_credentials(n_clicks_list, usernames, passwords):
    """Save the username/password for the row whose Save button was clicked."""

    if not ctx.triggered_id:
        return no_update

    sno = ctx.triggered_id["sno"]

    records = _read_team()

    # Find matching row by S NO
    found = False
    for r in records:
        if int(r["S NO"]) == int(sno):
            # Determine index in the pattern-match lists
            # The lists are ordered by sno (ALL pattern)
            all_snos = [int(rec["S NO"]) for rec in records]
            idx = all_snos.index(int(sno))

            new_user = str(usernames[idx] or "").strip()
            new_pass = str(passwords[idx] or "").strip()

            if not new_user or not new_pass:
                return dbc.Alert(
                    f"Both username and password are required for {r['Area']}",
                    color="warning",
                    duration=4000,
                )

            r["Username"] = new_user
            r["Password"] = new_pass
            found = True
            break

    if not found:
        return dbc.Alert("Row not found", color="danger", duration=3000)

    _save_team(records)

    area = next(r["Area"] for r in records if int(r["S NO"]) == int(sno))
    return dbc.Alert(
        f"Credentials saved for {area} ✔",
        color="success",
        duration=3000,
    )

@app.callback(
    Output({"type": "kyk-upload-status", "sno": MATCH}, "children"),
    Input({"type": "kyk-event-upload", "sno": MATCH}, "contents"),
    State({"type": "kyk-event-upload", "sno": MATCH}, "filename"),
    prevent_initial_call=True
)
def handle_event_upload(contents, filenames):
    if not contents:
        return no_update
    
    sno = ctx.triggered_id["sno"]
    records = _read_team()
    area = next((r["Area"] for r in records if int(r["S NO"]) == int(sno)), "Unknown")
    
    safe_area = "".join(c for c in area if c.isalnum() or c in " _-").strip()
    area_dir = os.path.join(EVENTS_DIR, safe_area)
    os.makedirs(area_dir, exist_ok=True)
    
    error_msgs = []
    
    for content, name in zip(contents, filenames):
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

        filepath = os.path.join(area_dir, name)
        with open(filepath, 'wb') as f:
            f.write(decoded)
            
    # Regenerate file list UI
    file_list_ui = []
    if error_msgs:
        file_list_ui.append(dbc.Alert(" | ".join(error_msgs), color="danger", duration=8000))

    for fname in os.listdir(area_dir):
        fpath = os.path.join(area_dir, fname)
        if os.path.isfile(fpath):
            file_list_ui.append(
                html.Div(
                    [
                        html.A(fname, href=f"/assets/upcoming_events/{safe_area}/{urllib.parse.quote(fname)}", target="_blank", className="text-decoration-none small", style={"maxWidth": "120px", "overflow": "hidden", "textOverflow": "ellipsis", "whiteSpace": "nowrap", "display": "inline-block"}),
                        html.Button(
                            "X",
                            id={"type": "kyk-del-event", "sno": sno, "filename": fname},
                            className="btn btn-sm btn-danger ms-2 py-0 px-1",
                            style={"fontSize": "10px", "lineHeight": "1"}
                        )
                    ],
                    className="d-flex align-items-center justify-content-between mb-1"
                )
            )

    return file_list_ui

@app.callback(
    Output("kyk-table-wrapper", "children"),
    Input({"type": "kyk-del-event", "sno": ALL, "filename": ALL}, "n_clicks"),
    prevent_initial_call=True
)
def handle_event_delete(n_clicks_list):
    if not any(n_clicks_list):
        return no_update
        
    trig = ctx.triggered_id
    sno = trig["sno"]
    filename = trig["filename"]
    
    records = _read_team()
    area = next((r["Area"] for r in records if int(r["S NO"]) == int(sno)), "Unknown")
    safe_area = "".join(c for c in area if c.isalnum() or c in " _-").strip()
    
    filepath = os.path.join(EVENTS_DIR, safe_area, filename)
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
        except Exception:
            pass
            
    # Refresh layout
    return _build_table(records)


# ══════════════════════════════════════════════════════════
# CALLBACKS — Tab 2: Image Deletion Requests (new)
# ══════════════════════════════════════════════════════════

@app.callback(
    Output("kyk-del-list-container", "children"),
    Input("kyk-del-refresh-interval", "n_intervals"),
    Input("kyk-del-ac0-allow-switch", "value"),
    prevent_initial_call=False,
)
def kyk_del_refresh_list(_interval_tick, ac0_allow_delete):
    """Load all pending deletion requests from progress + greenery CSVs."""
    allow_ac0 = bool(ac0_allow_delete)
    write_kayakalp_ac0_delete_allowed(allow_ac0)

    cards = []

    # Progress deletion requests
    for r in read_progress_del_csv():
        if r.get("status") == "pending":
            cards.append(_build_del_card(r, "progress", allow_ac0))

    # Greenery deletion requests
    for r in read_greenery_del_csv():
        if r.get("status") == "pending":
            cards.append(_build_del_card(r, "greenery", allow_ac0))

    # Red tag deletion requests
    for r in read_rt_del_csv():
        if r.get("status") == "pending":
            cards.append(_build_del_card(r, "red_tag", allow_ac0))

    if not cards:
        return dbc.Alert("No pending image deletion requests 🎉", color="info")
    return cards


# ── Approve deletion ──────────────────────────────────────
@app.callback(
    Output({"type": "kyk-del-result", "uid": MATCH, "source": MATCH}, "children"),
    Input({"type": "kyk-del-approve-btn", "uid": MATCH, "source": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def kyk_del_approve(_):
    uid = ctx.triggered_id["uid"]
    source = ctx.triggered_id["source"]

    if source == "progress":
        all_rows = read_progress_del_csv()
    elif source == "greenery":
        all_rows = read_greenery_del_csv()
    else:
        all_rows = read_rt_del_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Request not found", color="warning")

    area_code_val = _lookup_area_code_for_del_row(target, source)
    if str(area_code_val).strip() == "0" and not read_kayakalp_ac0_delete_allowed():
        return dbc.Alert(
            "Area Code 0 — deletion not allowed (enable 'Allow deletion' above)",
            color="warning",
            className="mt-2 py-1",
        )

    zone = target["zone"]
    dept = target["dept"]
    image_type = target.get("image_type", "")
    image_file = target.get("image_file", "")
    before_file = target.get("before_file", "")

    if source == "progress":
        folder = get_progress_folder(zone, dept)
    elif source == "greenery":
        folder = get_greenery_folder(zone, dept)
    else:
        folder = get_red_folder(zone, dept)

    if source == "red_tag":
        item_path = os.path.join(folder, target.get("item_file", ""))
        spec_path = os.path.join(folder, target.get("spec_file", ""))
        if os.path.isfile(item_path):
            os.remove(item_path)
        if os.path.isfile(spec_path):
            os.remove(spec_path)
            
        # Also perfectly scrub them from the `RED_TAG_PENDING_CSV` so the museum card disappears!
        rt_all = read_rt_pending_csv()
        rf_modified = [rt_row for rt_row in rt_all if not (rt_row.get("item_file") == target.get("item_file") and rt_row.get("spec_file") == target.get("spec_file"))]
        write_rt_pending_csv(rf_modified)
            
    elif image_type == "before":
        # Delete only the before image file — keep text.csv and area_code.csv
        # entries so Location Name, Area Code, Responsible Person are retained
        # for the replacement before image upload.
        path = os.path.join(folder, image_file)
        if os.path.isfile(path):
            os.remove(path)

    elif image_type == "after":
        # Delete only the after image
        path = os.path.join(folder, image_file)
        if os.path.isfile(path):
            os.remove(path)

    # Mark as approved
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "approved"

    if source == "progress":
        write_progress_del_csv(all_rows)
    elif source == "greenery":
        write_greenery_del_csv(all_rows)
    else:
        write_rt_del_csv(all_rows)

    return dbc.Alert("Image deleted ✔", color="success", className="mt-2 py-1")


# ── Reject deletion ──────────────────────────────────────
@app.callback(
    Output({"type": "kyk-del-result", "uid": MATCH, "source": MATCH}, "children", allow_duplicate=True),
    Input({"type": "kyk-del-reject-btn", "uid": MATCH, "source": MATCH}, "n_clicks"),
    prevent_initial_call=True,
)
def kyk_del_reject(_):
    uid = ctx.triggered_id["uid"]
    source = ctx.triggered_id["source"]

    if source == "progress":
        all_rows = read_progress_del_csv()
    elif source == "greenery":
        all_rows = read_greenery_del_csv()
    else:
        all_rows = read_rt_del_csv()

    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Request not found", color="warning")

    # Mark as rejected — image stays untouched
    for r in all_rows:
        if r["id"] == uid:
            r["status"] = "rejected"

    if source == "progress":
        write_progress_del_csv(all_rows)
    elif source == "greenery":
        write_greenery_del_csv(all_rows)
    else:
        write_rt_del_csv(all_rows)

    return dbc.Alert("Deletion rejected — image kept ✘", color="danger", className="mt-2 py-1")
