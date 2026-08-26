import os
import io
import csv
import uuid
import base64
from datetime import datetime, timedelta

import dash
from dash import html, dcc, Input, Output, State, ctx, MATCH, ALL
import dash_bootstrap_components as dbc
from PIL import Image

from apps.kayakalp_ac0_settings import read_kayakalp_ac0_delete_allowed


dash.register_page(__name__, path="/greenery")
BASE_PATH = "./assets/K5"
GREENERY_PENDING_CSV = "./Data/greenery_pending.csv"
GREENERY_PENDING_COLUMNS = [
    "id", "zone", "dept", "before_file", "after_file",
    "location_name", "sub_location_name", "responsible_person", "area_code",
    "status", "submitted_at", "rejection_remark", "rejected_at",
]
GREENERY_DEL_CSV = "./Data/greenery_del_requests.csv"
GREENERY_DEL_COLUMNS = [
    "id", "zone", "dept", "image_type", "image_file", "before_file",
    "status", "submitted_at",
]
IMG_FRAME_STYLE = {
    "width": "100%",
    "height": "280px",      
    "backgroundColor": "#111",
    "border": "1px solid #ccc",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "hidden",
}


IMG_STYLE = {
    "maxWidth": "100%",
    "maxHeight": "100%",
    "objectFit": "contain",
}

def get_area_csv(zone, dept):
    return os.path.join(get_greenery_folder(zone, dept), "area_code.csv")


def save_area_code(zone, dept, before_name, area_code):
    path = get_area_csv(zone, dept)
    exists = os.path.isfile(path)

    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["image_name", "area_code"])

        w.writerow([before_name, area_code])

def compress_image(contents, max_size=(1600, 1600), quality=70):
    _, encoded = contents.split(",")
    binary = base64.b64decode(encoded)
    img = Image.open(io.BytesIO(binary)).convert("RGB")
    img.thumbnail(max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=True)
    return buf.getvalue()

def img_to_uri(path):
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()

def get_greenery_folder(zone, dept):
    zone = zone.strip()
    dept = dept.strip()
    
    resolved_zone = zone
    if os.path.isdir(BASE_PATH):
        for name in os.listdir(BASE_PATH):
            if name.lower().strip() == zone.lower().strip():
                resolved_zone = name
                break
                
    zone_path = os.path.join(BASE_PATH, resolved_zone)
    resolved_dept = dept
    if os.path.isdir(zone_path):
        for name in os.listdir(zone_path):
            if name.lower().strip() == dept.lower().strip():
                resolved_dept = name
                break
                
    path = os.path.join(zone_path, resolved_dept, "greenery")
    os.makedirs(path, exist_ok=True)
    return path


def get_greenery_pending_folder(zone, dept):
    path = os.path.join(get_greenery_folder(zone, dept), "pending")
    os.makedirs(path, exist_ok=True)
    return path


def get_pending_folder(zone, dept):
    return get_greenery_pending_folder(zone, dept)


_greenery_pending_cache = {
    "data": [],
    "mtime": 0.0
}

def read_greenery_pending_csv():
    if not os.path.isfile(GREENERY_PENDING_CSV) or os.path.getsize(GREENERY_PENDING_CSV) == 0:
        return []
    try:
        mtime = os.path.getmtime(GREENERY_PENDING_CSV)
        if _greenery_pending_cache["data"] and _greenery_pending_cache["mtime"] == mtime:
            return [row.copy() for row in _greenery_pending_cache["data"]]
        with open(GREENERY_PENDING_CSV, newline="", encoding="utf-8") as f:
            data = list(csv.DictReader(f))
            _greenery_pending_cache["data"] = data
            _greenery_pending_cache["mtime"] = mtime
            return [row.copy() for row in data]
    except Exception:
        with open(GREENERY_PENDING_CSV, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


def write_greenery_pending_csv(rows):
    # Use retry loop / atomic replace to prevent file locking on Windows
    tmp_path = GREENERY_PENDING_CSV + ".tmp"
    try:
        with open(tmp_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=GREENERY_PENDING_COLUMNS, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                for col in GREENERY_PENDING_COLUMNS:
                    r.setdefault(col, "")
                w.writerow(r)
        
        import time
        max_retries = 15
        for i in range(max_retries):
            try:
                os.replace(tmp_path, GREENERY_PENDING_CSV)
                break
            except PermissionError:
                if i == max_retries - 1:
                    raise
                time.sleep(0.1)
    except Exception:
        if os.path.isfile(tmp_path):
            try:
                os.remove(tmp_path)
            except Exception:
                pass
        raise


def append_greenery_pending_row(row_dict):
    exists = os.path.isfile(GREENERY_PENDING_CSV) and os.path.getsize(GREENERY_PENDING_CSV) > 0

    if exists:
        with open(GREENERY_PENDING_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(GREENERY_PENDING_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")

    with open(GREENERY_PENDING_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GREENERY_PENDING_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)


def count_greenery_pending():
    return sum(1 for r in read_greenery_pending_csv() if r.get("status") == "pending")


def read_greenery_del_csv():
    if not os.path.isfile(GREENERY_DEL_CSV) or os.path.getsize(GREENERY_DEL_CSV) == 0:
        return []
    with open(GREENERY_DEL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_greenery_del_csv(rows):
    with open(GREENERY_DEL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GREENERY_DEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in GREENERY_DEL_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)


def append_greenery_del_row(row_dict):
    exists = os.path.isfile(GREENERY_DEL_CSV) and os.path.getsize(GREENERY_DEL_CSV) > 0
    if exists:
        with open(GREENERY_DEL_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(GREENERY_DEL_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(GREENERY_DEL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=GREENERY_DEL_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)


def get_text_csv(zone, dept):
    return os.path.join(get_greenery_folder(zone, dept), "text.csv")

def load_text_map(zone, dept):
    data = {}
    path = get_text_csv(zone, dept)
    if os.path.isfile(path):
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                data[r["before_image_name"]] = {
                    "text": r.get("text", ""),
                    "text2": r.get("text2", ""),
                }

    area_path = get_area_csv(zone, dept)
    if os.path.isfile(area_path):
        with open(area_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                img_name = r.get("image_name")
                if img_name:
                    if img_name not in data:
                        data[img_name] = {}
                    data[img_name]["area_code"] = r.get("area_code", "")

    return data


def save_text(zone, dept, before_name, text, text2):
    path = get_text_csv(zone, dept)
    exists = os.path.isfile(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if not exists:
            w.writerow(["before_image_name", "text", "text2"])
        w.writerow([before_name, text, text2])



_parse_files_cache = {}

def parse_files(folder):
    try:
        mtime = os.path.getmtime(folder)
        if folder in _parse_files_cache and _parse_files_cache[folder]["mtime"] == mtime:
            return [row.copy() for row in _parse_files_cache[folder]["rows"]]
    except Exception:
        mtime = 0.0

    rows = {}
    after_files = []

    for f in os.listdir(folder):
        if not f.lower().endswith(".jpg"):
            continue

        parts = f.split(".")
        if len(parts) < 3:
            continue

        try:
            idx = int(parts[0])
        except ValueError:
            continue

        is_after = len(parts) == 4 and parts[1] == "1"
        dt_str = parts[-2]

        try:
            dt = datetime.strptime(dt_str, "%d%m%Y%H%M%S")
        except ValueError:
            continue

        if not is_after:
            rows[f] = {
                "before": f,
                "after": None,
                "dt": dt,
            }
        else:
            after_files.append((f, idx, dt))

    # Second pass: match after files to their before entries
    # Use exact datetime match (==) because after filenames always embed the
    # exact same dt_str as their corresponding before file. The old <= condition
    # caused earlier befores with the same idx prefix (batch uploads) to steal
    # the match, resulting in the after appearing under the wrong before image.
    for f, idx, dt in after_files:
        matched = False
        for r in rows.values():
            if (
                r["after"] is None
                and r["before"].startswith(str(idx) + ".")
                and r["dt"] == dt
            ):
                r["after"] = f
                r["dt"] = dt
                matched = True
                break
        # If the before image was deleted, keep the after as a standalone entry
        if not matched:
            rows[f] = {
                "before": None,
                "after": f,
                "dt": dt,
            }

    res = sorted(rows.values(), key=lambda x: x["dt"], reverse=True)
    if mtime > 0.0:
        _parse_files_cache[folder] = {
            "rows": [row.copy() for row in res],
            "mtime": mtime
        }
    return res


UPLOAD_STYLE = {
    "height": "90px",
    "border": "2px dashed #888",
    "borderRadius": "8px",
    "textAlign": "center",
    "lineHeight": "90px",
}
PREVIEW_STYLE = {}
COMMENT_STYLE = {}


def image_with_date(folder, fname):
    dt_str = fname.split(".")[-2]
    dt = datetime.strptime(dt_str, "%d%m%Y%H%M%S")

    return html.Div(
        [
            html.Div(
                dt.strftime("Uploaded on %d-%m-%Y %I:%M %p"),
                className="text-muted small mb-1",
            ),
            html.Div(
                html.Img(
                    src=img_to_uri(os.path.join(folder, fname)),
                    style=IMG_STYLE,
                ),
                style=IMG_FRAME_STYLE,
            ),
        ]
    )


layout = dbc.Container(
    [
        html.H4("Greenery – Before / After",className="greenery-title"),
        html.Div(id="greenery-upload-container"),
        dbc.Row(
            [
                dbc.Col(dbc.Input(id="greenery-filter-area", placeholder="Search Area Code", type="text"), md=3),
                dbc.Col(dbc.Input(id="greenery-filter-location", placeholder="Search Location Name", type="text"), md=3),
                dbc.Col(dbc.Input(id="greenery-filter-person", placeholder="Search Responsible Person", type="text"), md=3),
                dbc.Col(dbc.Button("Search", id="greenery-search-btn", color="primary", className="w-100"), md=3),
            ],
            className="mb-4",
        ),
        html.Div(id="greenery-list-container"),
    ],
    fluid=True,
)

def upload_row(idx):
    return dbc.Card(
        dbc.CardBody(
            [
                dbc.Row(
                    [
                        dbc.Col(
                            [
                                html.Div("Before (max 30 images)"),
                                dcc.Upload(
                                    id={"type": "greenery-before-upload", "index": idx},
                                    multiple=True,
                                    children="Select Before Image(s)",
                                    style=UPLOAD_STYLE,
                                ),
                                dcc.Store(id={"type": "greenery-before-store", "index": idx}),
                            ],
                            md=2,
                        ),
                        dbc.Col(
                            html.Div("Select image(s)", id={"type": "greenery-comment-area", "index": idx}),
                            md=10,
                        ),
                    ]
                ),
                dbc.Button(
                    "Upload & Save",
                    id={"type": "save-greenery", "index": idx},
                    color="success",
                    className="mt-3",
                ),
            ]
        ),
        className="mb-4",
    )

def existing_row(folder, row, text, allow_ac0_delete=False):
    if row["before"]:
        before = image_with_date(folder, row["before"])
    else:
        # Provide upload to replace the deleted before image
        before = dcc.Upload(
            id={"type": "greenery-before-upload-existing", "after": row["after"]},
            children="Upload Before Image",
            className="upload-box",
        )

    if row["after"]:
        after = image_with_date(folder, row["after"])
    elif row["before"]:
        after = dcc.Upload(
            id={"type": "greenery-after-upload-existing", "before": row["before"]},
            children="Upload After Image",
            className="upload-box",
        )
    else:
        after = html.Div("No after image", style={"color": "#888", "fontSize": "14px"})

    # Delete buttons — hide for area code 0 unless Kayakalp admin allows it
    area_code_str = str(text.get("area_code", "")).strip()
    is_area_zero = area_code_str == "0"
    show_delete = allow_ac0_delete or not is_area_zero

    del_before_section = []
    if row["before"] and show_delete:
        del_before_section = [
            dbc.Button(
                "🗑 Delete Before",
                id={"type": "grn-del-before-btn", "file": row["before"]},
                color="danger",
                size="sm",
                className="mt-1",
            ),
            html.Div(
                id={"type": "grn-del-before-result", "file": row["before"]},
                className="small",
            ),
        ]

    del_after_section = []
    if row["after"] and show_delete:
        del_after_section = [
            dbc.Button(
                "🗑 Delete After",
                id={"type": "grn-del-after-btn", "file": row["after"], "before": row["before"] or ""},
                color="danger",
                size="sm",
                className="mt-1",
            ),
            html.Div(
                id={"type": "grn-del-after-result", "file": row["after"], "before": row["before"] or ""},
                className="small",
            ),
        ]

    return dbc.Card(
        dbc.CardBody(
            dbc.Row(
                [
                    dbc.Col([before] + del_before_section, md=5),

                    dbc.Col(
                        html.Div(
                            [
                                html.Div(
                                    [
                                        html.Span("Location Name: ", className="fw-bold"),
                                        html.Span(text.get("text", "")),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Span("Area Code: ", className="fw-bold"),
                                        html.Span(text.get("area_code", "")),
                                    ]
                                ),
                                html.Div(
                                    [
                                        html.Span("Responsible Person: ", className="fw-bold"),
                                        html.Span(text.get("text2", "")),
                                    ],
                                    className="text-muted",
                                ),

                            ]
                        ),
                        md=2,
                    ),

                    dbc.Col([after] + del_after_section, md=5),
                ]
            )
        ),
        className="mb-3 greenery-card",
    )


@dash.callback(
    Output("greenery-upload-container", "children"),
    Output("greenery-list-container", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
    Input("greenery-search-btn", "n_clicks"),
    State("greenery-filter-area", "value"),
    State("greenery-filter-location", "value"),
    State("greenery-filter-person", "value"),
)
def render_greenery(zone, dept, _n, f_area, f_loc, f_per):
    if not zone or not dept:
        return html.Div("Select TEC Zone and Department", className="text-muted"), ""

    folder = get_greenery_folder(zone, dept)
    text_map = load_text_map(zone, dept)
    rows = parse_files(folder)

    upload_ui = upload_row(len(rows) + 1)

    f_area = (f_area or "").strip().lower()
    f_loc = (f_loc or "").strip().lower()
    f_per = (f_per or "").strip().lower()

    allow_ac0_delete = read_kayakalp_ac0_delete_allowed()

    list_ui = []
    for r in rows:
        t_data = text_map.get(r["before"], {})
        
        c_area = str(t_data.get("area_code", "")).strip().lower()
        c_loc = str(t_data.get("text", "")).strip().lower()
        c_per = str(t_data.get("text2", "")).strip().lower()
        
        if f_area and f_area not in c_area:
            continue
        if f_loc and f_loc not in c_loc:
            continue
        if f_per and f_per not in c_per:
            continue
            
        list_ui.append(existing_row(folder, r, t_data, allow_ac0_delete))

    return upload_ui, list_ui

@dash.callback(
    Output({"type": "greenery-before-store", "index": MATCH}, "data"),
    Input({"type": "greenery-before-upload", "index": MATCH}, "contents"),
)
def greenery_store_before(c):
    # Cap at 30 images
    if c and len(c) > 30:
        c = c[:30]
    return c

@dash.callback(
    Output({"type": "greenery-after-per-img-store", "index": MATCH, "img": MATCH}, "data"),
    Output({"type": "greenery-after-per-img-preview", "index": MATCH, "img": MATCH}, "children"),
    Input({"type": "greenery-after-per-img-upload", "index": MATCH, "img": MATCH}, "contents"),
)
def greenery_store_and_preview_after_per_img(c):
    if not c:
        return None, ""
    preview = html.Div(
        html.Img(src=c, style=IMG_STYLE),
        style=IMG_FRAME_STYLE,
    )
    return c, preview

@dash.callback(
    Output({"type": "greenery-comment-area", "index": MATCH}, "children"),
    Input({"type": "greenery-before-store", "index": MATCH}, "data"),
)
def greenery_preview_before(befores):
    if not befores:
        return "Select image(s)"

    # Cap at 30
    befores = befores[:30]
    idx = ctx.triggered_id["index"]

    rows = []
    for i, img in enumerate(befores):
        rows.append(
            dbc.Row(
                [
                    dbc.Col(
                        [
                            html.Div("Before", className="fw-bold mb-1"),
                            html.Div(
                                html.Img(src=img, style=IMG_STYLE),
                                style=IMG_FRAME_STYLE,
                            ),
                        ],
                        md=4,
                    ),
                    dbc.Col(
                        html.Div(
                            [
                                html.Label("Area Code"),
                                dcc.Dropdown(
                                    id={
                                        "type": "greenery-area-code",
                                        "index": idx,
                                        "img": i,
                                    },
                                    options=[{"label": str(x), "value": x} for x in range(0, 111)],
                                    placeholder="Select Area Code",
                                    clearable=False,
                                    style={"width": "100%"},
                                ),
                                html.Label("Location Name", className="mt-2"),
                                dbc.Textarea(
                                    id={"type": "greenery-comment-text", "index": idx, "img": i},
                                    placeholder="Enter Location Name (required)",
                                    className="comment-box mb-2",
                                ),
                                html.Label("Sub Location Name"),
                                dbc.Input(
                                    id={
                                        "type": "greenery-sub-location-text",
                                        "index": idx,
                                        "img": i,
                                    },
                                    placeholder="Enter Sub Location Name (optional)",
                                    type="text",
                                    className="mb-2",
                                ),
                                html.Label("Responsible Person Name"),
                                dbc.Input(
                                    id={
                                        "type": "greenery-comment-text2",
                                        "index": idx,
                                        "img": i,
                                    },
                                    placeholder="Enter Responsible Person Name (optional)",
                                    type="text",
                                ),
                            ]
                        ),
                        md=3,
                    ),
                    dbc.Col(
                        [
                            html.Div("After", className="fw-bold mb-1"),
                            dcc.Upload(
                                id={
                                    "type": "greenery-after-per-img-upload",
                                    "index": idx,
                                    "img": i,
                                },
                                children="Select After Image",
                                style=UPLOAD_STYLE,
                            ),
                            dcc.Store(id={
                                "type": "greenery-after-per-img-store",
                                "index": idx,
                                "img": i,
                            }),
                            html.Div(id={
                                "type": "greenery-after-per-img-preview",
                                "index": idx,
                                "img": i,
                            }),
                        ],
                        md=5,
                    ),
                ],
                className="mb-3 border-bottom pb-3",
            )
        )

    return rows


@dash.callback(
    Output({"type": "greenery-comment-text", "index": MATCH, "img": MATCH}, "value"),
    Output({"type": "greenery-sub-location-text", "index": MATCH, "img": MATCH}, "value"),
    Output({"type": "greenery-comment-text2", "index": MATCH, "img": MATCH}, "value"),
    Input({"type": "greenery-area-code", "index": MATCH, "img": MATCH}, "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def greenery_autofill_from_area_code(ac_value, zone, dept):
    """Auto-populate location, sub-location, and person from area_master.csv."""
    if ac_value is None or not zone or not dept:
        return dash.no_update, dash.no_update, dash.no_update
    from apps.area_master_admin import read_area_master_for
    master = read_area_master_for(zone, dept)
    rec = master.get(int(ac_value), {})

    def_loc = rec.get("location_name", "")
    def_sub = rec.get("sub_location_name", "")
    def_per = rec.get("responsible_person", "")

    if int(ac_value) == 0 and not def_loc and not def_sub and not def_per:
        from apps.area_master_admin import get_exec_team_person
        def_loc = dept
        def_sub = dept
        def_per = get_exec_team_person(zone, dept)

    return (
        def_loc,
        def_sub,
        def_per,
    )


@dash.callback(
    Output({"type": "save-greenery", "index": MATCH}, "children"),
    Input({"type": "save-greenery", "index": MATCH}, "n_clicks"),
    State({"type": "greenery-before-store", "index": MATCH}, "data"),
    State({"type": "greenery-after-per-img-store", "index": MATCH, "img": ALL}, "data"),
    State({"type": "greenery-comment-text", "index": MATCH, "img": ALL}, "value"),
    State({"type": "greenery-sub-location-text", "index": MATCH, "img": ALL}, "value"),
    State({"type": "greenery-comment-text2", "index": MATCH, "img": ALL}, "value"),
    State({"type": "greenery-area-code", "index": MATCH, "img": ALL}, "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def greenery_save_all(_, befores, after_images, texts, sub_locs, texts2, area_codes, zone, dept):

    if not befores or any(not t or not t.strip() for t in texts):
        return "Location Name required ❌"

    pending_folder = get_pending_folder(zone, dept)
    idx = ctx.triggered_id["index"]
    base_time = datetime.now()

    # after_images list is parallel to befores (one per before image)
    for i, (img, txt, sl, txt2, ac) in enumerate(zip(befores, texts, sub_locs, texts2, area_codes)):
        save_time = base_time + timedelta(minutes=i)
        dt_str = save_time.strftime("%d%m%Y%H%M%S")
        upload_id = str(uuid.uuid4())[:8]

        before_name = f"{idx}.{dt_str}.jpg"
        with open(os.path.join(pending_folder, before_name), "wb") as f:
            f.write(compress_image(img))

        after_name = ""
        after_content = after_images[i] if i < len(after_images) else None
        if after_content:
            after_name = f"{idx}.1.{dt_str}.jpg"
            with open(os.path.join(pending_folder, after_name), "wb") as f:
                f.write(compress_image(after_content))

        append_greenery_pending_row({
            "id": upload_id,
            "zone": zone,
            "dept": dept,
            "before_file": before_name,
            "after_file": after_name,
            "location_name": txt.strip(),
            "sub_location_name": (sl or "").strip(),
            "responsible_person": (txt2 or "").strip(),
            "area_code": "" if ac is None else ac,
            "status": "pending",
            "submitted_at": base_time.strftime("%d-%m-%Y %H:%M:%S"),
        })

    return "Submitted for Approval ✔"


@dash.callback(
    Output({"type": "greenery-after-upload-existing", "before": MATCH}, "children"),
    Input({"type": "greenery-after-upload-existing", "before": MATCH}, "contents"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def greenery_save_after_existing(contents, zone, dept):
    if not contents:
        raise dash.exceptions.PreventUpdate

    before_file = ctx.triggered_id["before"]

    parts = before_file.split(".")
    idx = parts[0]
    dt_str = parts[-2]

    # Save to pending folder (not main folder)
    pending_folder = get_pending_folder(zone, dept)
    after_name = f"{idx}.1.{dt_str}.jpg"

    with open(os.path.join(pending_folder, after_name), "wb") as f:
        f.write(compress_image(contents))

    area_csv = get_area_csv(zone, dept)
    area_code = ""
    if os.path.isfile(area_csv):
        with open(area_csv, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("image_name") == before_file:
                    area_code = r.get("area_code", "")
                    break

    # Append pending approval row for the after image
    upload_id = str(uuid.uuid4())[:8]
    append_greenery_pending_row({
        "id": upload_id,
        "zone": zone,
        "dept": dept,
        "before_file": before_file,
        "after_file": after_name,
        "location_name": "",
        "sub_location_name": "",
        "responsible_person": "",
        "area_code": area_code,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })

    return "After image submitted for approval ✔"


@dash.callback(
    Output({"type": "greenery-before-upload-existing", "after": MATCH}, "children"),
    Input({"type": "greenery-before-upload-existing", "after": MATCH}, "contents"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def grn_save_before_existing(contents, zone, dept):
    if not contents:
        raise dash.exceptions.PreventUpdate

    after_file = ctx.triggered_id["after"]

    # After files have pattern: {idx}.1.{dt_str}.jpg
    parts = after_file.split(".")
    idx = parts[0]
    dt_str = parts[-2]

    # Save to pending folder
    pending_folder = get_greenery_pending_folder(zone, dept)
    before_name = f"{idx}.{dt_str}.jpg"

    with open(os.path.join(pending_folder, before_name), "wb") as f:
        f.write(compress_image(contents))

    # Append pending approval row for the before image
    upload_id = str(uuid.uuid4())[:8]
    append_greenery_pending_row({
        "id": upload_id,
        "zone": zone,
        "dept": dept,
        "before_file": before_name,
        "after_file": "",
        "location_name": "",
        "sub_location_name": "",
        "responsible_person": "",
        "area_code": "",
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })

    return "Before image submitted for approval ✔"


@dash.callback(
    Output({"type": "grn-del-before-result", "file": MATCH}, "children"),
    Input({"type": "grn-del-before-btn", "file": MATCH}, "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def grn_request_del_before(_, zone, dept):
    if not zone or not dept:
        raise dash.exceptions.PreventUpdate
    image_file = ctx.triggered_id["file"]
    ac = str(load_text_map(zone, dept).get(image_file, {}).get("area_code", "")).strip()
    if ac == "0" and not read_kayakalp_ac0_delete_allowed():
        return html.Span(
            "Area Code 0: turn on Allow deletion in Kayakalp admin first.",
            className="text-danger small",
        )
    upload_id = str(uuid.uuid4())[:8]
    append_greenery_del_row({
        "id": upload_id,
        "zone": zone,
        "dept": dept,
        "image_type": "before",
        "image_file": image_file,
        "before_file": image_file,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })
    return html.Span("Deletion requested ✔", className="text-success")


@dash.callback(
    Output({"type": "grn-del-after-result", "file": MATCH, "before": MATCH}, "children"),
    Input({"type": "grn-del-after-btn", "file": MATCH, "before": MATCH}, "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def grn_request_del_after(_, zone, dept):
    if not zone or not dept:
        raise dash.exceptions.PreventUpdate
    tid = ctx.triggered_id
    image_file = tid["file"]
    before_file = tid["before"]
    ac = str(load_text_map(zone, dept).get(before_file, {}).get("area_code", "")).strip()
    if ac == "0" and not read_kayakalp_ac0_delete_allowed():
        return html.Span(
            "Area Code 0: turn on Allow deletion in Kayakalp admin first.",
            className="text-danger small",
        )
    upload_id = str(uuid.uuid4())[:8]
    append_greenery_del_row({
        "id": upload_id,
        "zone": zone,
        "dept": dept,
        "image_type": "after",
        "image_file": image_file,
        "before_file": before_file,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })
    return html.Span("Deletion requested ✔", className="text-success")
