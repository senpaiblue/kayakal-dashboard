import os
import csv
import uuid
import base64
import io
from datetime import datetime

import dash
from dash import html, dcc, Input, Output, State, ctx, ALL, MATCH
import dash_bootstrap_components as dbc
from PIL import Image

dash.register_page(__name__, path="/red_tag_museum")

BASE_PATH = "./assets/K5"

# ── Pending CSV (shared with red_tag_admin.py) ────────────────────
RED_TAG_PENDING_CSV = "./Data/red_tag_pending.csv"
RED_TAG_COLUMNS = [
    "id", "zone", "dept", "item_file", "spec_file",
    "total_items", "total_evaluation", "sorted",
    "status", "submitted_at",
]
RED_TAG_DEL_CSV = "./Data/red_tag_del_requests.csv"
RED_TAG_DEL_COLUMNS = [
    "id", "zone", "dept", "image_type", "item_file", "spec_file",
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

# ---------- HELPERS ----------
def get_red_folder(zone, dept):
    from apps.progress import get_progress_folder
    folder = os.path.dirname(get_progress_folder(zone, dept))
    path = os.path.join(folder, "red")
    os.makedirs(path, exist_ok=True)
    return path


def get_red_pending_folder(zone, dept):
    path = os.path.join(get_red_folder(zone, dept), "pending")
    os.makedirs(path, exist_ok=True)
    return path


# ── CSV helpers (exported for red_tag_admin.py) ───────────────────
_rt_pending_cache = {
    "data": [],
    "mtime": 0.0
}

def read_rt_pending_csv():
    if not os.path.isfile(RED_TAG_PENDING_CSV) or os.path.getsize(RED_TAG_PENDING_CSV) == 0:
        return []
    try:
        mtime = os.path.getmtime(RED_TAG_PENDING_CSV)
        if _rt_pending_cache["data"] and _rt_pending_cache["mtime"] == mtime:
            return [row.copy() for row in _rt_pending_cache["data"]]
        with open(RED_TAG_PENDING_CSV, newline="", encoding="utf-8") as f:
            data = list(csv.DictReader(f))
            _rt_pending_cache["data"] = data
            _rt_pending_cache["mtime"] = mtime
            return [row.copy() for row in data]
    except Exception:
        with open(RED_TAG_PENDING_CSV, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def write_rt_pending_csv(rows):
    with open(RED_TAG_PENDING_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in RED_TAG_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)


def append_rt_pending_row(row_dict):
    exists = os.path.isfile(RED_TAG_PENDING_CSV) and os.path.getsize(RED_TAG_PENDING_CSV) > 0

    if exists:
        with open(RED_TAG_PENDING_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(RED_TAG_PENDING_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")

    with open(RED_TAG_PENDING_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)

def read_rt_del_csv():
    if not os.path.isfile(RED_TAG_DEL_CSV) or os.path.getsize(RED_TAG_DEL_CSV) == 0:
        return []
    with open(RED_TAG_DEL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_rt_del_csv(rows):
    with open(RED_TAG_DEL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_DEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in RED_TAG_DEL_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)

def append_rt_del_row(row_dict):
    exists = os.path.isfile(RED_TAG_DEL_CSV) and os.path.getsize(RED_TAG_DEL_CSV) > 0
    if exists:
        with open(RED_TAG_DEL_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(RED_TAG_DEL_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(RED_TAG_DEL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=RED_TAG_DEL_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)


# ── Image helpers ─────────────────────────────────────────────────
def img_to_uri(path):
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


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


_parse_red_images_cache = {}

def parse_red_images(folder):
    """Parse approved images from the main red folder."""
    try:
        mtime = os.path.getmtime(folder)
        if folder in _parse_red_images_cache and _parse_red_images_cache[folder]["mtime"] == mtime:
            return [(idx, data.copy()) for idx, data in _parse_red_images_cache[folder]["combos"]]
    except Exception:
        mtime = 0.0

    combos = {}

    for f in os.listdir(folder):
        if not f.lower().endswith(".jpg"):
            continue
        # Skip the pending subfolder
        if os.path.isdir(os.path.join(folder, f)):
            continue

        parts = f.split(".")
        if len(parts) < 3:
            continue
        try:
            idx_str = parts[0]
            # idx is a uuid now, so use as string key
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

    res = sorted(combos.items(), key=lambda x: x[1]["dt"], reverse=True)
    if mtime > 0.0:
        _parse_red_images_cache[folder] = {
            "combos": [(idx, data.copy()) for idx, data in res],
            "mtime": mtime
        }
    return res


def _load_approved_data():
    """Load data for approved red tag items from the pending CSV."""
    data = {}
    rows = read_rt_pending_csv()
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
    """Mark a red tag item as sorted in the CSV."""
    rows = read_rt_pending_csv()
    for r in rows:
        if r.get("id") == uid:
            r["sorted"] = "yes"
    write_rt_pending_csv(rows)


# ---------- LAYOUT ----------
layout = dbc.Container(
    [
        html.H3("Red Tag Museum", className="mb-3 text-danger"),

        dbc.Card(
            dbc.CardBody(
                [
                    html.H6("Upload New Red Tag Item", className="mb-3"),

                    dbc.Row(
                        [
                            dbc.Col(
                                [
                                    dcc.Upload(
                                        id="rt-item-upload",
                                        children=html.Div("Upload Item Image"),
                                        style={
                                            "border": "2px dashed #dc3545",
                                            "padding": "20px",
                                            "textAlign": "center",
                                            "borderRadius": "8px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    html.Div(id="rt-item-preview", className="mt-2"),
                                ],
                                md=5,
                            ),

                            dbc.Col(
                                [
                                    dcc.Upload(
                                        id="rt-spec-upload",
                                        children=html.Div("Upload Specification Image"),
                                        style={
                                            "border": "2px dashed #0d6efd",
                                            "padding": "20px",
                                            "textAlign": "center",
                                            "borderRadius": "8px",
                                            "cursor": "pointer",
                                        },
                                    ),
                                    html.Div(id="rt-spec-preview", className="mt-2"),
                                ],
                                md=5,
                            ),

                            dbc.Col(
                                dbc.Button(
                                    "Upload",
                                    id="rt-save-btn",
                                    color="danger",
                                    className="mt-2",
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
                                        id="rt-total-items",
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
                                        id="rt-item-value-input",
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
                                        id="rt-total-evaluation",
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

                    html.Div(id="rt-upload-msg", className="mt-2"),
                ]
            ),
            style=CARD_STYLE,
            className="mb-4",
        ),

        html.Div(id="rt-gallery"),
        dcc.Store(id="rt-refresh-flag"),

    ],
    fluid=True,
)

# ---------- SAVE UPLOAD (to pending) ----------
@dash.callback(
    Output("rt-upload-msg", "children"),
    Output("rt-refresh-flag", "data"),
    Input("rt-save-btn", "n_clicks"),
    State("rt-item-upload", "contents"),
    State("rt-spec-upload", "contents"),
    State("rt-total-items", "value"),
    State("rt-total-evaluation", "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def save_red_images(_, item_img, spec_img, total_items, total_eval, zone, dept):
    if not all([item_img, spec_img, zone, dept]):
        return (
            "❌ Both images are mandatory",
            dash.no_update,
        )

    if total_items is None or total_eval is None:
        return (
            "❌ Total Items and Total Evaluation are mandatory",
            dash.no_update,
        )

    pending_folder = get_red_pending_folder(zone, dept)
    uid = uuid.uuid4().hex[:12]
    dt = datetime.now().strftime("%d%m%Y%H%M%S")

    item_fname = f"{uid}.{dt}.jpg"
    spec_fname = f"{uid}.1.{dt}.jpg"

    with open(os.path.join(pending_folder, item_fname), "wb") as f:
        f.write(compress_image(item_img))

    with open(os.path.join(pending_folder, spec_fname), "wb") as f:
        f.write(compress_image(spec_img))

    # Append to pending CSV
    append_rt_pending_row({
        "id": uid,
        "zone": zone,
        "dept": dept,
        "item_file": item_fname,
        "spec_file": spec_fname,
        "total_items": total_items,
        "total_evaluation": total_eval,
        "sorted": "no",
        "status": "pending",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return (
        "✅ Uploaded — pending Execution Team approval",
        datetime.now().isoformat(),
    )


# ---------- REFRESH GALLERY (approved only) ----------
@dash.callback(
    Output("rt-gallery", "children"),
    Input("rt-refresh-flag", "data"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def render_gallery(_, zone, dept):
    if not zone or not dept:
        return html.Div("Select TEC Zone & Department", className="text-muted")

    folder = get_red_folder(zone, dept)
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

        # Sorted button (only show if not already sorted)
        sorted_btn = html.Div()
        if not is_sorted:
            sorted_btn = html.Div(
                dbc.Button(
                    "Mark as Sorted",
                    id={"type": "rt-sort-btn", "index": combo_idx},
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
                id={"type": "rt-req-del-btn", "index": combo_idx},
                value=f"{data.get('item', '')}|{data.get('spec', '')}",
                color="danger",
                size="sm",
                outline=True,
                className="mt-2 ms-2",
            ),
            className="text-center d-inline-block",
        )

        # Safely build image columns
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
                        html.Div(id={"type": "rt-del-msg", "index": combo_idx}, className="text-center mt-2")
                    ]
                ),
                style=CARD_STYLE,
                className="mb-4",
            )
        )

    return cards

# ---------- IMAGE PREVIEWS ----------
@dash.callback(
    Output("rt-item-preview", "children"),
    Input("rt-item-upload", "contents"),
    Input("rt-item-upload", "filename"),
)
def rt_preview_item_image(contents, filename):
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


@dash.callback(
    Output("rt-spec-preview", "children"),
    Input("rt-spec-upload", "contents"),
    Input("rt-spec-upload", "filename"),
)
def rt_preview_spec_image(contents, filename):
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


# ---------- MARK SORTED ----------
@dash.callback(
    Output("rt-refresh-flag", "data", allow_duplicate=True),
    Input({"type": "rt-sort-btn", "index": ALL}, "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def rt_mark_sorted(n_clicks_list, zone, dept):
    if not any(n_clicks_list) or not zone or not dept:
        raise dash.exceptions.PreventUpdate

    triggered = ctx.triggered_id
    if triggered is None:
        raise dash.exceptions.PreventUpdate

    combo_idx = triggered["index"]
    update_red_sorted(combo_idx)

    return datetime.now().isoformat()

# ---------- CALCULATE TOTAL EVALUATION ----------
@dash.callback(
    Output("rt-total-evaluation", "value"),
    Input("rt-total-items", "value"),
    Input("rt-item-value-input", "value"),
)
def calculate_rt_total_eval(items, val):
    if items is not None and val is not None:
        return items * val
    return None

# ---------- REQUEST DELETION ----------
@dash.callback(
    Output({"type": "rt-del-msg", "index": MATCH}, "children"),
    Input({"type": "rt-req-del-btn", "index": MATCH}, "n_clicks"),
    State({"type": "rt-req-del-btn", "index": MATCH}, "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def rt_request_deletion(n_clicks, btn_value, zone, dept):
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

    append_rt_del_row({
        "id": getattr(uuid, "uuid4")().hex[:12],
        "zone": zone,
        "dept": dept,
        "image_type": "red_tag",
        "item_file": item_file,
        "spec_file": spec_file,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })

    return dbc.Alert("Deletion requested ⏳", color="warning", className="py-1 mt-2")
