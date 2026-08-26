
import os
import base64
from datetime import datetime
from app import app
import pandas as pd
from dash import Dash, html, dcc, callback, Input, Output, State, ctx, MATCH, ALL
import dash_bootstrap_components as dbc
import dash
import csv
import uuid

DT_PATH = "./assets/5s/DT.xlsx"   

D5S_DEL_CSV = "./Data/d5s_del_requests.csv"
D5S_DEL_COLUMNS = ["id", "dept", "model", "month", "year", "type", "file", "status", "submitted_at"]

def read_d5s_del_csv():
    os.makedirs("./Data", exist_ok=True)
    if not os.path.isfile(D5S_DEL_CSV) or os.path.getsize(D5S_DEL_CSV) == 0:
        return []
    with open(D5S_DEL_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))

def write_d5s_del_csv(rows):
    os.makedirs("./Data", exist_ok=True)
    with open(D5S_DEL_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=D5S_DEL_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in D5S_DEL_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)

def append_d5s_del_row(row_dict):
    os.makedirs("./Data", exist_ok=True)
    exists = os.path.isfile(D5S_DEL_CSV) and os.path.getsize(D5S_DEL_CSV) > 0
    if exists:
        with open(D5S_DEL_CSV, "rb") as f:
            f.seek(-1, 2)
            if f.read(1) != b"\n":
                with open(D5S_DEL_CSV, "a", encoding="utf-8") as fa:
                    fa.write("\n")
    with open(D5S_DEL_CSV, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=D5S_DEL_COLUMNS)
        if not exists:
            w.writeheader()
        w.writerow(row_dict)

if not os.path.exists(DT_PATH):
    raise FileNotFoundError(f"{DT_PATH} not found. Put your DT.xlsx there.")

df_dt = pd.read_excel(DT_PATH, dtype=str)  
df_dt['department'] = df_dt['department'].fillna('').astype(str)
df_dt['model'] = df_dt['model'].fillna('').astype(str)
df_dt['leader'] = df_dt['leader'].fillna('').astype(str)
def read_dt_fresh():
    df = pd.read_excel(DT_PATH, dtype=str)
    df = df.fillna("")
    return df
from docx import Document

def read_audit_summary(folder, month, year):
    fname = f"{month}{year}.docx"
    path = os.path.join(folder, fname)

    if not os.path.exists(path):
        return None

    doc = Document(path)
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return text


@callback(
    Output("dd_model", "options"),
    Output("dd_model", "value"),
    Input("dd_department", "value"),
)
def filter_models_by_department(selected_dept):
    if not selected_dept:
        return [], None

    df = read_dt_fresh()   

    filtered_rows = df[df["department"] == selected_dept]

    models = sorted(
        m for m in filtered_rows["model"].unique() if m
    )

    options = [{"label": m, "value": m} for m in models]

    return options, None



months = ["january","february","march","april","may","june",
          "july","august","september","october","november","december"]


def encode_image_to_datauri(path):
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    return f"data:image/jpg;base64,{data}"


def make_month_buttons(active_month):
    buttons = []
    for m in months:
        buttons.append(
            dbc.Button(
                m.capitalize(),
                id={"type": "month-btn", "month": m},
                color="success" if m == active_month else "secondary",
                className="me-1 mb-2",
                n_clicks=0,
                size="sm",
            )
        )
    return buttons


def list_before_images(folder, month, year):
    out = []
    if not os.path.exists(folder):
        return out

    for f in sorted(os.listdir(folder)):
        low = f.lower()
        if (
            low.endswith((".jpg", ".jpeg", ".png"))
            and month in low
            and str(year) in low
            and ".1" not in low    
        ):
            out.append(f)
    return out



from app import app


# Fixed viewport so Before/After pairs share the same height regardless of upload aspect ratio.
D5S_IMAGE_VIEWPORT_HEIGHT = "340px"
D5S_IMAGE_VIEWPORT_BASE = {
    "width": "100%",
    "height": D5S_IMAGE_VIEWPORT_HEIGHT,
    "minHeight": D5S_IMAGE_VIEWPORT_HEIGHT,
    "overflow": "hidden",
    "borderRadius": "4px",
    "backgroundColor": "#111",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "boxSizing": "border-box",
}
D5S_IMAGE_FILL = {
    "maxWidth": "100%",
    "maxHeight": "100%",
    "width": "auto",
    "height": "auto",
    "objectFit": "contain",
    "display": "block",
}


def d5s_framed_image(src, border_color):
    """Image letterboxed inside a constant-height frame (same viewport for every upload)."""
    return html.Div(
        html.Img(src=src, style=D5S_IMAGE_FILL),
        style={**D5S_IMAGE_VIEWPORT_BASE, "border": f"3px solid {border_color}"},
    )


styles = {
    "before_after_label": {"fontWeight": "600", "marginBottom": "6px"},
    "upload_box": {
        "width": "100%",
        
        "height": "110px",
        "border": "2px dashed #6c757d",
        "textAlign": "center",
        "borderRadius": "4px",
        "backgroundColor": "#fafafa",
        "paddingTop": "10px",
        "boxSizing": "border-box"
    },
    "after_preview_wrap": {
        "width": "100%",
        "marginTop": "6px",
    },
    "col_left": {
        "paddingRight": "12px",
        "borderRight": "1px solid #ccc"
    },
    "col_right": {
        "paddingLeft": "12px"
    },
    "filename_text": {"fontSize": "12px", "color": "#333", "marginTop": "6px"}
}
layout = dbc.Container([
    html.H2("5S Audit - Image Upload (Before / After)"),
    html.Hr(),

   
    dbc.Row([
        dbc.Col([
            html.Label("Department"),
            dcc.Dropdown(
                id="dd_department",
                options=[],         
                placeholder="Select Department",
                value=None
            )

        ], md=4),
        
        dbc.Col([
            html.Label("Model Area"),
            dcc.Dropdown(
                id="dd_model",
                options=[],          
                placeholder="Select Model Area",
                value=None
            )

        ], md=4),

        dbc.Col([
            html.Br(),
            dbc.Button("Show Data", id="btn_show", color="primary")
        ], md=2)
    ], className="my-3"),
    html.Div(
        id="audit_summary",
        className="p-3 mb-3",
        style={
            "border": "1px solid #ccc",
            "backgroundColor": "#f8f9fa",
            "whiteSpace": "pre-line"
        }
    ),

    dcc.Store(id="selected", data={}),
    dcc.Store(id="active-month", data=None),
    dcc.Store(id="active-year", data=datetime.now().year),

    dbc.Row([
        dbc.Col([
            html.Label("Year"),
            dcc.Dropdown(
                id="dd_year",
                options=[],   
                value=datetime.now().year,
                clearable=False
            )
        ], md=2),
    ], className="mb-2"),

    html.Hr(),
    
    html.Div(id="main_content"),
    dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Upload Authorization")),
        dbc.ModalBody([
            html.Div("Enter password to upload image", className="mb-2"),
            dbc.Input(
                id="upload-password",
                type="password",
                placeholder="Password"
            ),
            html.Div(id="pwd-error", className="text-danger mt-2")
        ]),
        dbc.ModalFooter(
            dbc.Button("Verify", id="btn-verify-pwd", color="primary")
        ),
    ],
    id="pwd-modal",
    is_open=False,
    backdrop="static",
    centered=True,
    ),
    dcc.Store(id="pwd-ok", data=False),
    dcc.Store(id="pending-upload-index", data=None),
    dcc.Store(id="last-unlock-ts", data=0),



], fluid=True)
import re

@callback(
    Output("dd_year", "options"),
    Output("dd_year", "value"),
    Input("dd_department", "value"),
    Input("dd_model", "value"),
)
def load_years(dept, model):
    if not dept or not model:
        return [], None

    folder = os.path.join("assets", "5s", str(dept), str(model))
    years = set()

    if os.path.exists(folder):
        for f in os.listdir(folder):
            low = f.lower()

            if low.endswith((".jpg", ".jpeg", ".png", ".docx")):
                match = re.search(r"(20\d{2})", low)
                if match:
                    years.add(int(match.group(1)))

    
    current_year = datetime.now().year
    years.add(current_year - 2)
    years.add(current_year - 1)
    years.add(current_year)
    years.add(current_year + 1)

    years_sorted = sorted(years, reverse=True)

    options = [{"label": y, "value": y} for y in years_sorted]

    return options, years_sorted[0]




@callback(
    Output("dd_department", "options"),
    Input("dd_department", "id")  ) 
def load_departments(_):
    df = read_dt_fresh()

    departments = sorted(
        d for d in df["department"].unique() if d
    )

    return [{"label": d, "value": d} for d in departments]


@callback(
    Output("main_content", "children"),
    Output("selected", "data"),
    Input("btn_show", "n_clicks"),
    State("dd_department", "value"),
    State("dd_model", "value"),
    prevent_initial_call=True
)
def on_show(n_clicks, dept, model):
    if not dept or not model:
        return dbc.Alert("Please select both Department and Model Area.", color="danger"), {}

  
    df_live = read_dt_fresh()

    row = df_live[
        (df_live['department'] == str(dept)) &
        (df_live['model'] == str(model))
    ]

    leader = row['leader'].values[0] if not row.empty else "Not Assigned"

    active_month = datetime.now().strftime("%B").lower()

    header = html.Div([
        html.H5(f"Team Leader – {leader}", className="mb-2"),
        html.Div(make_month_buttons(active_month), id="month_buttons_area"),
        html.H6(
            f"Showing images for {active_month.capitalize()}",
            id="images_title",
            className="mt-2"
        ),
        dcc.Store(id="active-month-initial", data=active_month),
        html.Div(id="images_container")
    ])

    selected_data = {"dept": dept, "model": model, "leader": leader}
    return header, selected_data




@callback(
    Output("images_container", "children"),
    Output("images_title", "children"),
    Output("month_buttons_area", "children"),
    Output("active-month", "data"),
    Output("audit_summary", "children"),  
    Input({"type": "month-btn", "month": ALL}, "n_clicks"),
    Input("dd_year", "value"),            
    State("selected", "data"),
    State("active-month", "data"),
    State("active-month-initial", "data"),
    prevent_initial_call=True
)

def on_month_click(
    all_clicks,
    selected_year,
    selected,
    active_month_store,
    active_month_initial
):
    sel = selected or {}
    dept = sel.get("dept")
    model = sel.get("model")

    if not dept or not model:
        return (
            dbc.Alert("Please select Department and Model and click Show Data.", color="danger"),
            "Showing images",
            make_month_buttons(datetime.now().strftime("%B").lower()),
            datetime.now().strftime("%B").lower(),
            dbc.Alert("No audit summary available.", color="info")
        )

    triggered = ctx.triggered_id
    if isinstance(triggered, dict) and triggered.get("month"):
        clicked_month = triggered["month"]
    else:
        clicked_month = active_month_store or active_month_initial or datetime.now().strftime("%B").lower()

    folder = os.path.join("assets", "5s", str(dept), str(model))
    os.makedirs(folder, exist_ok=True)

    year = selected_year or datetime.now().year

    summary_text = read_audit_summary(folder, clicked_month, year)

    summary_ui = (
        html.Div([
            html.Div([
                html.H6(f"Audit Summary – {clicked_month.capitalize()} {year}", style={"display": "inline-block", "marginRight": "15px", "marginBottom": "0px"}),
                dbc.Button(
                    "🗑 Request Delete Summary",
                    id="d5s-del-summary-btn",
                    size="sm",
                    color="danger",
                    className="py-1 px-2"
                ),
                html.Span(id="d5s-del-summary-result", style={"marginLeft": "15px", "fontSize": "13px"})
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "10px"}),
            html.Div(summary_text)
        ])
        if summary_text
        else dbc.Alert(
            f"No audit summary available for {clicked_month.capitalize()} {year}.",
            color="info"
        )
    )

    
    before_images = list_before_images(folder, clicked_month, year)

    if not before_images:
        content = dbc.Alert(
            f"No before-images found for {clicked_month.capitalize()}.",
            color="warning"
        )
        buttons = make_month_buttons(clicked_month)

        return (
            content,
            f"Showing images for {clicked_month.capitalize()}",
            buttons,
            clicked_month,
            summary_ui   )

 
    rows = []

    for idx, fname in enumerate(before_images, start=1):
        before_path = os.path.join(folder, fname)
        before_uri = encode_image_to_datauri(before_path)

        after_name = f"{idx}.1{clicked_month}{year}.jpg"
        after_path = os.path.join(folder, after_name)

        after_preview = None
        if os.path.exists(after_path):
            after_preview = d5s_framed_image(
                encode_image_to_datauri(after_path), "#1e7e34"
            )

        left_col = dbc.Col([
            html.Div([
                html.Span("Before", style={**styles["before_after_label"], "marginRight": "10px", "marginBottom": "0"}),
                dbc.Button(
                    "🗑 Request Delete",
                    id={"type": "d5s-del-before-btn", "index": idx},
                    size="sm",
                    color="danger",
                    className="py-0 px-2",
                    style={"fontSize": "11px"}
                ),
                html.Span(id={"type": "d5s-del-before-result", "index": idx}, style={"marginLeft": "10px", "fontSize": "12px"})
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}),
            d5s_framed_image(before_uri, "#222"),
            html.Div(fname, style=styles["filename_text"])
        ], md=6, style=styles["col_left"])

        right_col = dbc.Col([
            html.Div([
                html.Span("After", style={**styles["before_after_label"], "marginRight": "10px", "marginBottom": "0"}),
                dbc.Button(
                    "🗑 Request Delete",
                    id={"type": "d5s-del-after-btn", "index": idx},
                    size="sm",
                    color="danger",
                    className="py-0 px-2",
                    style={"fontSize": "11px", "display": "inline-block" if after_preview else "none"}
                ),
                html.Span(id={"type": "d5s-del-after-result", "index": idx}, style={"marginLeft": "10px", "fontSize": "12px"})
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "6px"}),
            dbc.Button(
                "Unlock Upload",
                id={"type": "unlock-btn", "index": idx},
                size="sm",
                color="warning",
                className="mb-1"
            ),
            dcc.Upload(
                id={"type": "upload", "index": idx},
                disabled=True,
                children=html.Div("Drag & Drop or Click to Upload"),
                style=styles["upload_box"],
                multiple=False
            ),
            html.Div(
                after_preview,
                id={"type": "after-preview", "index": idx},
                style=styles["after_preview_wrap"]
            )
        ], md=6, style=styles["col_right"])

        rows.append(dbc.Row([left_col, right_col], align="stretch", className="mb-4"))

    return (
        rows,
        f"Showing images for {clicked_month.capitalize()}",
        make_month_buttons(clicked_month),
        clicked_month,
        summary_ui
    )


@callback(
    Output({"type": "after-preview", "index": MATCH}, "children"),
    Input({"type": "upload", "index": MATCH}, "contents"),
    State({"type": "upload", "index": MATCH}, "filename"),
    State("selected", "data"),
    State("active-month", "data"),
    State("dd_year", "value"),        
    prevent_initial_call=True
)
def handle_upload(contents, filename, selected, active_month, selected_year):

    if contents is None:
        raise dash.exceptions.PreventUpdate

    dept = selected.get("dept")
    model = selected.get("model")
    if not dept or not model:
        return dbc.Alert("Dept/model not provided", color="danger")

    triggered_id = ctx.triggered_id
    if not isinstance(triggered_id, dict):
        raise Exception("Invalid trigger id")
    idx = triggered_id.get("index")

   
    month = active_month or datetime.now().strftime("%B").lower()
    year = selected_year or datetime.now().year
    save_name = f"{idx}.1{month}{year}.jpg"

    folder = os.path.join("assets", "5s", str(dept), str(model))
    os.makedirs(folder, exist_ok=True)
    save_path = os.path.join(folder, save_name)

    content_type, content_string = contents.split(',')
    binary = base64.b64decode(content_string)
    with open(save_path, "wb") as f:
        f.write(binary)

    
    return d5s_framed_image(
        f"data:image/jpg;base64,{content_string}",
        "#1e7e34",
    )

@callback(
    Output("pwd-modal", "is_open"),
    Output("pending-upload-index", "data"),
    Output("pwd-ok", "data"),
    Output("pwd-error", "children"),
    Output("last-unlock-ts", "data"),
    Input({"type": "unlock-btn", "index": ALL}, "n_clicks"),
    Input("btn-verify-pwd", "n_clicks"),
    State("upload-password", "value"),
    State("selected", "data"),
    State("pending-upload-index", "data"),
    State("last-unlock-ts", "data"),
    prevent_initial_call=True
)
def password_flow(unlock_clicks, verify_click, entered_pwd,
                  selected, pending_idx, last_ts):

    trigger = ctx.triggered_id

   
    if isinstance(trigger, dict) and trigger.get("type") == "unlock-btn":
        idx = trigger.get("index")
        ts = unlock_clicks[idx - 1]

        
        if ts is None or ts <= last_ts:
            raise dash.exceptions.PreventUpdate

        return True, idx, False, "", ts

    
    if trigger == "btn-verify-pwd":
        dept = selected.get("dept")
        model = selected.get("model")

        df_live = read_dt_fresh()  

        row = df_live[
            (df_live["department"] == str(dept)) &
            (df_live["model"] == str(model))
        ]

        correct_pwd = row["password"].values[0] if not row.empty else ""

        if entered_pwd == correct_pwd:
            return False, pending_idx, True, "", last_ts

        return True, pending_idx, False, "❌ Invalid password", last_ts


    raise dash.exceptions.PreventUpdate
@callback(
    Output({"type": "upload", "index": MATCH}, "disabled"),
    Input("pwd-ok", "data"),
    prevent_initial_call=True
)
def enable_upload(pwd_ok):
    return not pwd_ok


@callback(
    Output("d5s-del-summary-result", "children"),
    Input("d5s-del-summary-btn", "n_clicks"),
    State("selected", "data"),
    State("active-month", "data"),
    State("dd_year", "value"),
    prevent_initial_call=True
)
def d5s_request_delete_summary(n_clicks, selected, active_month, selected_year):
    if not n_clicks:
        return ""
    dept = selected.get("dept")
    model = selected.get("model")
    if not dept or not model:
        return dbc.Alert("Department and Model Area must be selected first.", color="warning", style={"padding": "2px 5px", "margin": "0"})
    
    month = active_month or datetime.now().strftime("%B").lower()
    year = selected_year or datetime.now().year
    filename = f"{month}{year}.docx"
    
    # Check if request already exists
    reqs = read_d5s_del_csv()
    for r in reqs:
        if r.get("dept") == str(dept) and r.get("model") == str(model) and r.get("type") == "summary" and r.get("file") == filename and r.get("status") == "pending":
            return html.Span("Deletion already requested ✔", className="text-warning")
            
    req_id = str(uuid.uuid4())[:8]
    append_d5s_del_row({
        "id": req_id,
        "dept": str(dept),
        "model": str(model),
        "month": str(month),
        "year": str(year),
        "type": "summary",
        "file": filename,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })
    return html.Span("Deletion requested ✔", className="text-success")


@callback(
    Output({"type": "d5s-del-before-result", "index": MATCH}, "children"),
    Input({"type": "d5s-del-before-btn", "index": MATCH}, "n_clicks"),
    State("selected", "data"),
    State("active-month", "data"),
    State("dd_year", "value"),
    prevent_initial_call=True
)
def d5s_request_delete_before(n_clicks, selected, active_month, selected_year):
    if not n_clicks:
        return ""
    dept = selected.get("dept")
    model = selected.get("model")
    if not dept or not model:
        return ""
    
    idx = ctx.triggered_id["index"]
    month = active_month or datetime.now().strftime("%B").lower()
    year = selected_year or datetime.now().year
    
    folder = os.path.join("assets", "5s", str(dept), str(model))
    before_images = list_before_images(folder, month, year)
    if not before_images or len(before_images) < idx:
        return html.Span("Image not found", className="text-danger")
        
    filename = before_images[idx - 1]
    
    # Check if request already exists
    reqs = read_d5s_del_csv()
    for r in reqs:
        if r.get("dept") == str(dept) and r.get("model") == str(model) and r.get("type") == "before" and r.get("file") == filename and r.get("status") == "pending":
            return html.Span("Deletion already requested ✔", className="text-warning")
            
    req_id = str(uuid.uuid4())[:8]
    append_d5s_del_row({
        "id": req_id,
        "dept": str(dept),
        "model": str(model),
        "month": str(month),
        "year": str(year),
        "type": "before",
        "file": filename,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })
    return html.Span("Deletion requested ✔", className="text-success")


@callback(
    Output({"type": "d5s-del-after-result", "index": MATCH}, "children"),
    Input({"type": "d5s-del-after-btn", "index": MATCH}, "n_clicks"),
    State("selected", "data"),
    State("active-month", "data"),
    State("dd_year", "value"),
    prevent_initial_call=True
)
def d5s_request_delete_after(n_clicks, selected, active_month, selected_year):
    if not n_clicks:
        return ""
    dept = selected.get("dept")
    model = selected.get("model")
    if not dept or not model:
        return ""
    
    idx = ctx.triggered_id["index"]
    month = active_month or datetime.now().strftime("%B").lower()
    year = selected_year or datetime.now().year
    
    filename = f"{idx}.1{month}{year}.jpg"
    
    # Check if request already exists
    reqs = read_d5s_del_csv()
    for r in reqs:
        if r.get("dept") == str(dept) and r.get("model") == str(model) and r.get("type") == "after" and r.get("file") == filename and r.get("status") == "pending":
            return html.Span("Deletion already requested ✔", className="text-warning")
            
    req_id = str(uuid.uuid4())[:8]
    append_d5s_del_row({
        "id": req_id,
        "dept": str(dept),
        "model": str(model),
        "month": str(month),
        "year": str(year),
        "type": "after",
        "file": filename,
        "status": "pending",
        "submitted_at": datetime.now().strftime("%d-%m-%Y %H:%M:%S"),
    })
    return html.Span("Deletion requested ✔", className="text-success")


