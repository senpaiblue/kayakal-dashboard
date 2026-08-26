import os
import csv
import uuid
import base64
import io
import shutil
import pandas as pd
from datetime import datetime

import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH, callback
import dash_bootstrap_components as dbc
from PIL import Image

from app import app

# ---------- CONFIG ----------
DT_PATH = "./assets/5s/DT.xlsx"
BASE_5S_PATH = "./assets/5s"

RED_TAG_5S_PENDING_CSV = "./Data/red_tag_5s_pending.csv"
RED_TAG_5S_COLUMNS = [
    "id", "dept", "model", "item_file", "spec_file",
    "total_items", "total_evaluation", "sorted",
    "status", "submitted_at", "contact_phone"
]

RED_TAG_5S_DEL_CSV = "./Data/red_tag_5s_del_requests.csv"
RED_TAG_5S_DEL_COLUMNS = [
    "id", "dept", "model", "image_type", "item_file", "spec_file",
    "status", "submitted_at"
]

# ---------- STYLES ----------
IMG_FRAME = {
    "width": "100%",
    "height": "280px",
    "backgroundColor": "#111",
    "border": "2px solid #ddd",
    "borderRadius": "8px",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "hidden",
    "transition": "transform 0.3s",
}

IMG_STYLE = {
    "maxWidth": "100%",
    "maxHeight": "100%",
    "objectFit": "contain",
}

CARD_STYLE = {
    "boxShadow": "0 6px 18px rgba(0,0,0,0.1)",
    "borderRadius": "10px",
    "animation": "fadeIn 0.4s ease-in",
}

INPUT_STYLE = {
    "width": "100%",
    "padding": "10px",
    "borderRadius": "10px",
    "border": "1px solid #d1d5db",
    "fontSize": "14px"
}

# ---------- HELPERS ----------
def read_dt_fresh():
    df = pd.read_excel(DT_PATH, dtype=str)
    df = df.fillna("")
    return df

def load_departments():
    try:
        df = read_dt_fresh()
        return sorted(d for d in df["department"].unique() if d)
    except Exception:
        return []

def load_model_areas(dept):
    if not dept:
        return []
    try:
        df = read_dt_fresh()
        filtered_rows = df[df["department"] == dept]
        return sorted(m for m in filtered_rows["model"].unique() if m)
    except Exception:
        return []

def get_5s_red_folder(dept, model):
    path = os.path.join(BASE_5S_PATH, str(dept).strip(), str(model).strip(), "red")
    os.makedirs(path, exist_ok=True)
    return path

def get_5s_red_pending_folder(dept, model):
    path = os.path.join(get_5s_red_folder(dept, model), "pending")
    os.makedirs(path, exist_ok=True)
    return path

def read_rt_5s_pending_csv():
    if not os.path.isfile(RED_TAG_5S_PENDING_CSV) or os.path.getsize(RED_TAG_5S_PENDING_CSV) == 0:
        return []
    with open(RED_TAG_5S_PENDING_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_rt_5s_pending_csv(rows):
    os.makedirs(os.path.dirname(RED_TAG_5S_PENDING_CSV), exist_ok=True)
    with open(RED_TAG_5S_PENDING_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_5S_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in RED_TAG_5S_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)

def append_rt_5s_pending_row(row_dict):
    os.makedirs(os.path.dirname(RED_TAG_5S_PENDING_CSV), exist_ok=True)
    exists = os.path.isfile(RED_TAG_5S_PENDING_CSV) and os.path.getsize(RED_TAG_5S_PENDING_CSV) > 0
    if exists:
        with open(RED_TAG_5S_PENDING_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(RED_TAG_5S_PENDING_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(RED_TAG_5S_PENDING_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_5S_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)

def read_rt_5s_del_csv():
    if not os.path.isfile(RED_TAG_5S_DEL_CSV) or os.path.getsize(RED_TAG_5S_DEL_CSV) == 0:
        return []
    with open(RED_TAG_5S_DEL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_rt_5s_del_csv(rows):
    os.makedirs(os.path.dirname(RED_TAG_5S_DEL_CSV), exist_ok=True)
    with open(RED_TAG_5S_DEL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_5S_DEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in RED_TAG_5S_DEL_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)

def append_rt_5s_del_row(row_dict):
    os.makedirs(os.path.dirname(RED_TAG_5S_DEL_CSV), exist_ok=True)
    exists = os.path.isfile(RED_TAG_5S_DEL_CSV) and os.path.getsize(RED_TAG_5S_DEL_CSV) > 0
    if exists:
        with open(RED_TAG_5S_DEL_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(RED_TAG_5S_DEL_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(RED_TAG_5S_DEL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_5S_DEL_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)

def img_to_uri(path):
    if not path or not os.path.isfile(path):
        return ""
    try:
        with open(path, "rb") as f:
            return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return ""

def readable_dt(fname):
    try:
        dt = datetime.strptime(fname.split(".")[-2], "%d%m%Y%H%M%S")
        return dt.strftime("Uploaded on %d-%m-%Y at %I:%M %p")
    except Exception:
        return ""

def compress_image(contents, size=(1600, 1600), quality=70):
    _, encoded = contents.split(",")
    binary = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(binary)).convert("RGB")
    img.thumbnail(size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def _load_approved_data():
    data = {}
    rows = read_rt_5s_pending_csv()
    for r in rows:
        if r.get("status") == "approved":
            uid = r.get("id", "")
            data[uid] = {
                "total_items": r.get("total_items", ""),
                "total_evaluation": r.get("total_evaluation", ""),
                "sorted": r.get("sorted", "no"),
            }
    return data

def update_red_sorted(uid):
    rows = read_rt_5s_pending_csv()
    for r in rows:
        if r.get("id") == uid:
            r["sorted"] = "yes"
    write_rt_5s_pending_csv(rows)

def parse_red_images(folder):
    combos = {}
    if not os.path.exists(folder):
        return []
    for f in os.listdir(folder):
        if not f.lower().endswith(".jpg"):
            continue
        if os.path.isdir(os.path.join(folder, f)):
            continue
        parts = f.split(".")
        if len(parts) < 3:
            continue
        try:
            idx_str = parts[0]
            is_spec = parts[1] == "1"
            dt = datetime.strptime(parts[-2], "%d%m%Y%H%M%S")
        except (ValueError, IndexError):
            continue

        combos.setdefault(idx_str, {"item": None, "spec": None, "dt": dt})
        if is_spec:
            combos[idx_str]["spec"] = f
            combos[idx_str]["dt"] = dt
        else:
            combos[idx_str]["item"] = f

    return sorted(combos.items(), key=lambda x: x[1]["dt"], reverse=True)

# ---------- LAYOUT ----------
layout = dbc.Container(
    [
        html.Div([
            html.H2("5S Red Tag Museum", style={"marginBottom": "4px", "fontWeight": "700"}),
            html.P("Upload and manage 5S Red Tag items department-wise", style={"color": "#6b7280"})
        ], style={"marginBottom": "24px"}),

        dbc.Card(
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Department"),
                        dcc.Dropdown(
                            id="rt5s-dd-department",
                            options=[{"label": d, "value": d} for d in load_departments()],
                            placeholder="Select Department",
                            value=None,
                            clearable=False
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label("Model Area"),
                        dcc.Dropdown(
                            id="rt5s-dd-model",
                            options=[],
                            placeholder="Select Model Area",
                            value=None,
                            clearable=False
                        )
                    ], md=4),
                    dbc.Col([
                        html.Label(" "),
                        dbc.Button(
                            "🔓 Unlock Approvals",
                            id="rt5s-unlock-btn",
                            color="dark",
                            className="w-100 mt-1"
                        )
                    ], md=4)
                ])
            ]),
            className="control-card mb-4"
        ),

        dbc.Tabs(
            [
                dbc.Tab(label="Upload Red Tags", tab_id="rt5s-tab-upload"),
                dbc.Tab(label="See Uploaded Red Tags", tab_id="rt5s-tab-view"),
            ],
            id="rt5s-sub-tabs",
            active_tab="rt5s-tab-upload",
            className="mb-4"
        ),

        # Upload Container
        html.Div(
            id="rt5s-upload-container",
            children=[
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H5("Upload New Red Tag Item", className="mb-3"),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            dcc.Upload(
                                                id="rt5s-item-upload",
                                                children=html.Div("Upload Item Image"),
                                                style={
                                                    "border": "2px dashed #dc3545",
                                                    "padding": "20px",
                                                    "textAlign": "center",
                                                    "borderRadius": "8px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            html.Div(id="rt5s-item-preview", className="mt-2"),
                                        ],
                                        md=5,
                                    ),
                                    dbc.Col(
                                        [
                                            dcc.Upload(
                                                id="rt5s-spec-upload",
                                                children=html.Div("Upload Specification Image"),
                                                style={
                                                    "border": "2px dashed #0d6efd",
                                                    "padding": "20px",
                                                    "textAlign": "center",
                                                    "borderRadius": "8px",
                                                    "cursor": "pointer",
                                                },
                                            ),
                                            html.Div(id="rt5s-spec-preview", className="mt-2"),
                                        ],
                                        md=5,
                                    ),
                                    dbc.Col(
                                        dbc.Button(
                                            "Upload",
                                            id="rt5s-save-btn",
                                            color="danger",
                                            className="mt-2 w-100",
                                        ),
                                        md=2,
                                        className="d-flex align-items-center",
                                    ),
                                ]
                            ),
                            dbc.Row(
                                [
                                    dbc.Col(
                                        [
                                            html.Label("Total Items"),
                                            dcc.Input(
                                                id="rt5s-total-items",
                                                type="number",
                                                min=0,
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Item Value"),
                                            dcc.Input(
                                                id="rt5s-item-value-input",
                                                type="number",
                                                min=0,
                                                step=0.01,
                                                style={"width": "100%"},
                                            ),
                                        ],
                                        md=4,
                                    ),
                                    dbc.Col(
                                        [
                                            html.Label("Total Evaluation"),
                                            dcc.Input(
                                                id="rt5s-total-evaluation",
                                                type="number",
                                                min=0,
                                                step=0.01,
                                                readOnly=True,
                                                style={
                                                    "width": "100%",
                                                    "backgroundColor": "#e9ecef",
                                                    "fontWeight": "bold",
                                                },
                                            ),
                                        ],
                                        md=4,
                                    ),
                                ],
                                className="mt-3",
                            ),
                            html.Div(id="rt5s-upload-msg", className="mt-2"),
                        ]
                    ),
                    style=CARD_STYLE,
                    className="mb-4",
                )
            ]
        ),

        # View Container
        html.Div(
            id="rt5s-view-container",
            children=[
                html.Div(id="rt5s-gallery"),
                # Admin approvals section (unlocked by password)
                html.Div(id="rt5s-approvals-container"),
            ]
        ),

        # PASSWORD MODAL
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Unlock Admin / Approvals")),
                dbc.ModalBody([
                    html.Div("Enter password of the selected Department and Model Area to unlock approvals", className="mb-2"),
                    dbc.Input(
                        id="rt5s-upload-password",
                        type="password",
                        placeholder="Password"
                    ),
                    html.Div(id="rt5s-pwd-error", className="text-danger mt-2")
                ]),
                dbc.ModalFooter(
                    dbc.Button("Verify", id="rt5s-btn-verify-pwd", color="primary")
                ),
            ],
            id="rt5s-pwd-modal",
            backdrop="static",
            centered=True,
            is_open=False,
        ),

        dcc.Store(id="rt5s-pwd-ok", data=False),
        dcc.Store(id="rt5s-refresh-flag", data=None),
        dcc.Store(id="rt5s-admin-refresh-flag", data=None),
    ],
    fluid=True,
)

# ---------- PASSWORD FLOW CALLBACKS ----------
@app.callback(
    Output("rt5s-pwd-modal", "is_open"),
    Output("rt5s-pwd-ok", "data"),
    Output("rt5s-pwd-error", "children"),
    Input("rt5s-unlock-btn", "n_clicks"),
    Input("rt5s-btn-verify-pwd", "n_clicks"),
    State("rt5s-pwd-ok", "data"),
    State("rt5s-upload-password", "value"),
    State("rt5s-dd-department", "value"),
    State("rt5s-dd-model", "value"),
    prevent_initial_call=True
)
def handle_rt5s_unlock_and_verify(unlock_click, verify_click, pwd_ok, entered_pwd, dept, model):
    trigger = ctx.triggered_id
    if not trigger:
        raise dash.exceptions.PreventUpdate

    if trigger == "rt5s-unlock-btn":
        if not dept or not model:
            return False, False, "Please select Department and Model Area first."
        if pwd_ok:
            return False, pwd_ok, ""
        return True, False, ""

    if trigger == "rt5s-btn-verify-pwd":
        if not dept or not model:
            return True, False, "Please select Department and Model Area first."
        df = read_dt_fresh()
        row = df[
            (df["department"] == str(dept)) &
            (df["model"] == str(model))
        ]
        correct_pwd = row["password"].values[0] if not row.empty else ""
        if entered_pwd == correct_pwd:
            return False, True, ""
        return True, False, "❌ Invalid password"

    raise dash.exceptions.PreventUpdate

@app.callback(
    Output("rt5s-pwd-ok", "data", allow_duplicate=True),
    Input("rt5s-dd-department", "value"),
    Input("rt5s-dd-model", "value"),
    prevent_initial_call=True
)
def reset_pwd_ok(dept, model):
    return False

# ---------- DROPDOWNS & VALUE CALLBACKS ----------
@app.callback(
    Output("rt5s-dd-model", "options"),
    Input("rt5s-dd-department", "value")
)
def update_rt5s_model_options(dept):
    areas = load_model_areas(dept)
    return [{"label": a, "value": a} for a in areas]

@app.callback(
    Output("rt5s-total-evaluation", "value"),
    Input("rt5s-total-items", "value"),
    Input("rt5s-item-value-input", "value"),
)
def calculate_rt5s_total_eval(items, val):
    if items is not None and val is not None:
        return items * val
    return None

# ---------- SAVE UPLOAD CALLBACK ----------
@app.callback(
    Output("rt5s-upload-msg", "children"),
    Output("rt5s-refresh-flag", "data"),
    Input("rt5s-save-btn", "n_clicks"),
    State("rt5s-item-upload", "contents"),
    State("rt5s-spec-upload", "contents"),
    State("rt5s-total-items", "value"),
    State("rt5s-total-evaluation", "value"),
    State("rt5s-dd-department", "value"),
    State("rt5s-dd-model", "value"),
    prevent_initial_call=True,
)
def save_5s_red_images(_, item_img, spec_img, total_items, total_eval, dept, model):
    if not all([item_img, spec_img, dept, model]):
        return (
            "❌ Both images, Department, and Model Area are mandatory",
            dash.no_update,
        )

    if total_items is None or total_eval is None:
        return (
            "❌ Total Items and Total Evaluation are mandatory",
            dash.no_update,
        )

    pending_folder = get_5s_red_pending_folder(dept, model)
    uid = uuid.uuid4().hex[:12]
    dt = datetime.now().strftime("%d%m%Y%H%M%S")

    item_fname = f"{uid}.{dt}.jpg"
    spec_fname = f"{uid}.1.{dt}.jpg"

    with open(os.path.join(pending_folder, item_fname), "wb") as f:
        f.write(compress_image(item_img))

    with open(os.path.join(pending_folder, spec_fname), "wb") as f:
        f.write(compress_image(spec_img))

    append_rt_5s_pending_row({
        "id": uid,
        "dept": dept,
        "model": model,
        "item_file": item_fname,
        "spec_file": spec_fname,
        "total_items": total_items,
        "total_evaluation": total_eval,
        "sorted": "no",
        "status": "pending",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "contact_phone": ""
    })

    return (
        "✅ Uploaded — pending Department & Model Area admin approval",
        datetime.now().isoformat(),
    )

# ---------- IMAGE PREVIEW CALLBACKS ----------
@app.callback(
    Output("rt5s-item-preview", "children"),
    Input("rt5s-item-upload", "contents"),
    Input("rt5s-item-upload", "filename"),
)
def rt5s_preview_item_image(contents, filename):
    if not contents:
        return ""
    return html.Div(
        [
            html.Small(f"\u2714 {filename}", className="text-success d-block mb-1"),
            html.Div(
                html.Img(src=contents, style=IMG_STYLE),
                style=IMG_FRAME,
            ),
        ]
    )

@app.callback(
    Output("rt5s-spec-preview", "children"),
    Input("rt5s-spec-upload", "contents"),
    Input("rt5s-spec-upload", "filename"),
)
def rt5s_preview_spec_image(contents, filename):
    if not contents:
        return ""
    return html.Div(
        [
            html.Small(f"\u2714 {filename}", className="text-success d-block mb-1"),
            html.Div(
                html.Img(src=contents, style=IMG_STYLE),
                style=IMG_FRAME,
            ),
        ]
    )

# ---------- GALLERY RENDERING & SORT/DELETE CALLBACKS ----------
@app.callback(
    Output("rt5s-gallery", "children"),
    Input("rt5s-refresh-flag", "data"),
    Input("rt5s-admin-refresh-flag", "data"),
    Input("rt5s-dd-department", "value"),
    Input("rt5s-dd-model", "value"),
)
def render_rt5s_gallery(_, _admin, dept, model):
    if not dept or not model:
        return html.Div("Select Department & Model Area", className="text-muted")

    folder = get_5s_red_folder(dept, model)
    combos = parse_red_images(folder)
    approved_data = _load_approved_data()

    if not combos:
        return dbc.Alert("No approved Red Tag items yet.", color="info")

    cards = []
    for combo_idx, data in combos:
        rd = approved_data.get(combo_idx, {})
        ti = rd.get("total_items", "")
        te = rd.get("total_evaluation", "")
        is_sorted = rd.get("sorted", "no") == "yes"

        info_row = []
        if ti:
            info_row.append(
                html.Span(
                    f"Total Items: {ti}",
                    className="badge bg-secondary me-2",
                    style={"fontSize": "13px"},
                )
            )
            
        try:
            if ti and te:
                iv_val = float(te) / float(ti)
                iv_str = f"{iv_val:g}"
                info_row.append(
                    html.Span(
                        f"Item Value: {iv_str}",
                        className="badge bg-warning text-dark me-2",
                        style={"fontSize": "13px"},
                    )
                )
        except (ValueError, TypeError, ZeroDivisionError):
            pass

        if te:
            info_row.append(
                html.Span(
                    f"Total Evaluation: {te}",
                    className="badge bg-info me-2",
                    style={"fontSize": "13px"},
                )
            )
        if is_sorted:
            info_row.append(
                html.Span(
                    "Sorted \u2714",
                    className="badge bg-success",
                    style={"fontSize": "13px"},
                )
            )

        # Sorted button
        sorted_btn = html.Div()
        if not is_sorted:
            sorted_btn = html.Div(
                dbc.Button(
                    "Mark as Sorted",
                    id={"type": "rt5s-sort-btn", "index": combo_idx},
                    color="success",
                    size="sm",
                    className="mt-2",
                ),
                className="text-center",
            )

        # Deletion Button
        req_del_btn = html.Div(
            dbc.Button(
                "🗑️ Request Deletion",
                id={"type": "rt5s-req-del-btn", "index": combo_idx},
                value=f"{data.get('item', '')}|{data.get('spec', '')}",
                color="danger",
                size="sm",
                outline=True,
                className="mt-2 ms-2",
            ),
            className="text-center d-inline-block",
        )

        img_cols = []
        if data.get("item") and os.path.isfile(os.path.join(folder, data["item"])):
            img_cols.append(
                dbc.Col(
                    html.Div(
                        html.Img(
                            src=img_to_uri(os.path.join(folder, data["item"])),
                            style=IMG_STYLE,
                        ),
                        style=IMG_FRAME,
                    ),
                    md=6,
                )
            )
        if data.get("spec") and os.path.isfile(os.path.join(folder, data["spec"])):
            img_cols.append(
                dbc.Col(
                    html.Div(
                        html.Img(
                            src=img_to_uri(os.path.join(folder, data["spec"])),
                            style=IMG_STYLE,
                        ),
                        style=IMG_FRAME,
                    ),
                    md=6,
                )
            )

        cards.append(
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            readable_dt(data.get("spec") or data.get("item") or ""),
                            className="text-center fw-semibold mb-2",
                        ),
                        html.Div(
                            info_row,
                            className="text-center mb-2",
                        ) if info_row else html.Div(),
                        dbc.Row(img_cols),
                        html.Div(
                            [sorted_btn, req_del_btn],
                            className="d-flex justify-content-center mt-2"
                        ),
                        html.Div(id={"type": "rt5s-del-msg", "index": combo_idx}, className="text-center mt-2")
                    ]
                ),
                style=CARD_STYLE,
                className="mb-4",
            )
        )

    return cards

@app.callback(
    Output("rt5s-refresh-flag", "data", allow_duplicate=True),
    Input({"type": "rt5s-sort-btn", "index": ALL}, "n_clicks"),
    prevent_initial_call=True,
)
def rt5s_mark_sorted(n_clicks_list):
    if not any(n_clicks_list):
        raise dash.exceptions.PreventUpdate

    triggered = ctx.triggered_id
    if triggered is None:
        raise dash.exceptions.PreventUpdate

    combo_idx = triggered["index"]
    update_red_sorted(combo_idx)
    return datetime.now().isoformat()

@app.callback(
    Output({"type": "rt5s-del-msg", "index": MATCH}, "children"),
    Input({"type": "rt5s-req-del-btn", "index": MATCH}, "n_clicks"),
    State({"type": "rt5s-req-del-btn", "index": MATCH}, "value"),
    State("rt5s-dd-department", "value"),
    State("rt5s-dd-model", "value"),
    prevent_initial_call=True,
)
def rt5s_request_deletion(n_clicks, btn_value, dept, model):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate

    triggered = ctx.triggered_id
    uid = triggered["index"]
    
    item_file = ""
    spec_file = ""
    if btn_value:
        parts = btn_value.split("|")
        if len(parts) == 2:
            item_file, spec_file = parts[0], parts[1]

    append_rt_5s_del_row({
        "id": uuid.uuid4().hex[:12],
        "dept": dept,
        "model": model,
        "image_type": "red_tag",
        "item_file": item_file,
        "spec_file": spec_file,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return dbc.Alert("Deletion requested ⏳", color="warning", className="py-1 mt-2")

# ---------- ADMIN APPROVALS RENDERING CALLBACK ----------
@app.callback(
    Output("rt5s-approvals-container", "children"),
    Input("rt5s-pwd-ok", "data"),
    Input("rt5s-dd-department", "value"),
    Input("rt5s-dd-model", "value"),
    Input("rt5s-admin-refresh-flag", "data"),
)
def render_rt5s_approvals(pwd_ok, dept, model, _refresh):
    if not pwd_ok or not dept or not model:
        return html.Div()

    pending_uploads = [
        r for r in read_rt_5s_pending_csv()
        if r.get("status") == "pending" and r.get("dept") == dept and r.get("model") == model
    ]

    pending_deletes = [
        r for r in read_rt_5s_del_csv()
        if r.get("status") == "pending" and r.get("dept") == dept and r.get("model") == model
    ]

    upload_cards = []
    for r in pending_uploads:
        uid = r["id"]
        pending_folder = get_5s_red_pending_folder(dept, model)
        item_path = os.path.join(pending_folder, r.get("item_file", ""))
        spec_path = os.path.join(pending_folder, r.get("spec_file", ""))

        item_uri = img_to_uri(item_path) if os.path.isfile(item_path) else ""
        spec_uri = img_to_uri(spec_path) if os.path.isfile(spec_path) else ""

        ti = r.get("total_items", "")
        te = r.get("total_evaluation", "")
        iv = ""
        try:
            if ti and te:
                iv = f"{float(te) / float(ti):g}"
        except (ValueError, TypeError, ZeroDivisionError):
            pass

        upload_cards.append(
            dbc.Card(
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Small("Item Image", className="fw-bold text-muted"),
                            html.Div(html.Img(src=item_uri, style=IMG_STYLE) if item_uri else "No image", style=IMG_FRAME),
                        ], md=4),
                        dbc.Col([
                            html.Small("Specification Image", className="fw-bold text-muted"),
                            html.Div(html.Img(src=spec_uri, style=IMG_STYLE) if spec_uri else "No image", style=IMG_FRAME),
                        ], md=4),
                        dbc.Col([
                            html.Div([
                                html.Div([html.Span("Total Items: ", className="fw-bold"), html.Span(ti)]),
                                html.Div([html.Span("Item Value: ", className="fw-bold"), html.Span(iv)]) if iv else html.Div(),
                                html.Div([html.Span("Total Evaluation: ", className="fw-bold"), html.Span(te)]),
                                html.Div([html.Span("Submitted: ", className="fw-bold"), html.Span(r.get("submitted_at", ""))], className="text-muted small mt-1"),
                                html.Div([
                                    dbc.Button("✔ Approve", id={"type": "rt5s-approve-btn", "uid": uid}, color="success", size="sm", className="me-2"),
                                    dbc.Button("✘ Reject", id={"type": "rt5s-reject-btn", "uid": uid}, color="danger", size="sm"),
                                ], className="mt-3"),
                            ]),
                        ], md=4),
                    ]),
                    html.Div(id={"type": "rt5s-approve-result", "uid": uid})
                ]),
                className="mb-3 shadow-sm"
            )
        )

    delete_cards = []
    for r in pending_deletes:
        uid = r["id"]
        main_folder = get_5s_red_folder(dept, model)
        item_path = os.path.join(main_folder, r.get("item_file", ""))
        spec_path = os.path.join(main_folder, r.get("spec_file", ""))

        item_uri = img_to_uri(item_path) if os.path.isfile(item_path) else ""
        spec_uri = img_to_uri(spec_path) if os.path.isfile(spec_path) else ""

        delete_cards.append(
            dbc.Card(
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Small("Item Image (To Delete)", className="fw-bold text-muted"),
                            html.Div(html.Img(src=item_uri, style=IMG_STYLE) if item_uri else "No image", style=IMG_FRAME),
                        ], md=4),
                        dbc.Col([
                            html.Small("Specification Image (To Delete)", className="fw-bold text-muted"),
                            html.Div(html.Img(src=spec_uri, style=IMG_STYLE) if spec_uri else "No image", style=IMG_FRAME),
                        ], md=4),
                        dbc.Col([
                            html.Div([
                                html.Div([html.Span("Status: ", className="fw-bold"), html.Span("Deletion Requested")]),
                                html.Div([html.Span("Submitted: ", className="fw-bold"), html.Span(r.get("submitted_at", ""))], className="text-muted small mt-1"),
                                html.Div([
                                    dbc.Button("✔ Approve Deletion", id={"type": "rt5s-del-approve-btn", "uid": uid}, color="success", size="sm", className="me-2"),
                                    dbc.Button("✘ Reject Deletion", id={"type": "rt5s-del-reject-btn", "uid": uid}, color="danger", size="sm"),
                                ], className="mt-3"),
                            ]),
                        ], md=4),
                    ]),
                    html.Div(id={"type": "rt5s-del-result", "uid": uid})
                ]),
                className="mb-3 shadow-sm border-danger"
            )
        )

    sections = []
    if upload_cards:
        sections.append(html.H5("Pending Red Tag Uploads", className="text-primary mt-3 mb-2"))
        sections.extend(upload_cards)
    if delete_cards:
        sections.append(html.H5("Pending Deletion Requests", className="text-danger mt-3 mb-2"))
        sections.extend(delete_cards)

    if not sections:
        return dbc.Alert("No pending approvals 🎉", color="info", className="mt-3")

    return html.Div(sections)

# ---------- ADMIN APPROVE/REJECT CALLBACKS ----------
@app.callback(
    Output({"type": "rt5s-approve-result", "uid": MATCH}, "children"),
    Input({"type": "rt5s-approve-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "rt5s-reject-btn", "uid": MATCH}, "n_clicks"),
    State("rt5s-dd-department", "value"),
    State("rt5s-dd-model", "value"),
    prevent_initial_call=True,
)
def handle_rt5s_approve_or_reject(approve_clicks, reject_clicks, dept, model):
    if not ctx.triggered_id:
        raise dash.exceptions.PreventUpdate

    uid = ctx.triggered_id["uid"]
    btn_type = ctx.triggered_id["type"]

    all_rows = read_rt_5s_pending_csv()
    target = None
    for r in all_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Not found", color="warning")

    pending_folder = get_5s_red_pending_folder(dept, model)
    main_folder = get_5s_red_folder(dept, model)

    if btn_type == "rt5s-approve-btn":
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

        for r in all_rows:
            if r["id"] == uid:
                r["status"] = "approved"
        write_rt_5s_pending_csv(all_rows)

        return dbc.Alert("Approved ✔", color="success", className="mt-2 py-1")

    elif btn_type == "rt5s-reject-btn":
        # Delete item image
        src_item = os.path.join(pending_folder, target.get("item_file", ""))
        if os.path.isfile(src_item):
            os.remove(src_item)

        # Delete spec image
        src_spec = os.path.join(pending_folder, target.get("spec_file", ""))
        if os.path.isfile(src_spec):
            os.remove(src_spec)

        all_rows = [r for r in all_rows if r["id"] != uid]
        write_rt_5s_pending_csv(all_rows)

        return dbc.Alert("Rejected & Deleted ✘", color="danger", className="mt-2 py-1")

    raise dash.exceptions.PreventUpdate

@app.callback(
    Output({"type": "rt5s-del-result", "uid": MATCH}, "children"),
    Input({"type": "rt5s-del-approve-btn", "uid": MATCH}, "n_clicks"),
    Input({"type": "rt5s-del-reject-btn", "uid": MATCH}, "n_clicks"),
    State("rt5s-dd-department", "value"),
    State("rt5s-dd-model", "value"),
    prevent_initial_call=True,
)
def handle_rt5s_del_approve_or_reject(approve_clicks, reject_clicks, dept, model):
    if not ctx.triggered_id:
        raise dash.exceptions.PreventUpdate

    uid = ctx.triggered_id["uid"]
    btn_type = ctx.triggered_id["type"]

    all_del_rows = read_rt_5s_del_csv()
    target = None
    for r in all_del_rows:
        if r["id"] == uid:
            target = r
            break

    if not target:
        return dbc.Alert("Request not found", color="warning")

    main_folder = get_5s_red_folder(dept, model)

    if btn_type == "rt5s-del-approve-btn":
        item_path = os.path.join(main_folder, target.get("item_file", ""))
        spec_path = os.path.join(main_folder, target.get("spec_file", ""))
        if os.path.isfile(item_path):
            os.remove(item_path)
        if os.path.isfile(spec_path):
            os.remove(spec_path)

        pending_rows = read_rt_5s_pending_csv()
        pending_rows = [
            pr for pr in pending_rows
            if not (pr.get("item_file") == target.get("item_file") and pr.get("spec_file") == target.get("spec_file"))
        ]
        write_rt_5s_pending_csv(pending_rows)

        for r in all_del_rows:
            if r["id"] == uid:
                r["status"] = "approved"
        write_rt_5s_del_csv(all_del_rows)

        return dbc.Alert("Deletion Approved ✔", color="success", className="mt-2 py-1")

    elif btn_type == "rt5s-del-reject-btn":
        for r in all_del_rows:
            if r["id"] == uid:
                r["status"] = "rejected"
        write_rt_5s_del_csv(all_del_rows)

        return dbc.Alert("Deletion Rejected ✘", color="danger", className="mt-2 py-1")

    raise dash.exceptions.PreventUpdate


# ---------- DEDICATED REFRESH FLAG UPDATER (watches ALL result components) ----------
@app.callback(
    Output("rt5s-admin-refresh-flag", "data", allow_duplicate=True),
    Input({"type": "rt5s-approve-result", "uid": ALL}, "children"),
    Input({"type": "rt5s-del-result", "uid": ALL}, "children"),
    prevent_initial_call=True,
)
def rt5s_sync_admin_refresh_flag(approve_results, del_results):
    """Watches all approve/del result components for any change and triggers admin refresh."""
    if not ctx.triggered_id:
        raise dash.exceptions.PreventUpdate
    return datetime.now().isoformat()


# ---------- TOGGLE SUB-TABS CALLBACK ----------
@app.callback(
    Output("rt5s-upload-container", "style"),
    Output("rt5s-view-container", "style"),
    Input("rt5s-sub-tabs", "active_tab")
)
def toggle_sub_tabs(active_tab):
    if active_tab == "rt5s-tab-upload":
        return {"display": "block"}, {"display": "none"}
    else:
        return {"display": "none"}, {"display": "block"}
