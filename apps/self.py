import os
import base64
import re
from datetime import datetime
import pandas as pd
import dash
from dash import html, dcc, Input, Output, ctx, MATCH, ALL, callback, State
import dash_bootstrap_components as dbc
from server import app


DT_PATH = "./assets/5s/DT.xlsx"

# ===== FIXED-HEIGHT IMAGE VIEW (Before / After) =====
from datetime import datetime

current_year = datetime.now().year
year_options = [current_year - 2, current_year - 1, current_year,
                current_year + 1, current_year + 2]
IMG_FRAME_STYLE = {
    "width": "100%",
    "height": "340px",
    "minHeight": "340px",
    "backgroundColor": "#111",
    "border": "1px solid #999",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "hidden",
    "boxSizing": "border-box",
}

IMG_STYLE = {
    "maxWidth": "100%",
    "maxHeight": "100%",
    "width": "auto",
    "height": "auto",
    "objectFit": "contain",
    "display": "block",
}




# ============================
# LIVE EXCEL READER
# ============================
def read_dt_fresh():
    """Always fresh read — used by ALL callbacks"""
    df = pd.read_excel(DT_PATH, dtype=str)
    return df.fillna("")

def preview_img(path):
    return html.Div(
        html.Img(src=img_to_uri(path), style=IMG_STYLE),
        style=IMG_FRAME_STYLE
    )

# ============================
# IMAGE HELPERS
# ============================
def img_to_uri(path):
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


MONTHS = [
    "january","february","march","april","may","june",
    "july","august","september","october","november","december"
]


# ============================
# SELF FOLDER PER MODEL
# ============================
def get_self_folder(dept, model):
    base = os.path.join("assets","5s",str(dept),str(model))
    os.makedirs(base, exist_ok=True)

    selff = os.path.join(base, "self")
    os.makedirs(selff, exist_ok=True)

    return selff



# ============================
# LIST SLOT IMAGES
# ============================
def list_images_for_month(dept, model, month, year, side):

    folder = get_self_folder(dept, model)
    out = []
    print("FOLDER =", repr(folder))
    print("EXISTS =", os.path.exists(folder))

    for f in sorted(os.listdir(folder)):
        low = f.lower()

        if not low.endswith((".jpg",".jpeg",".png")):
            continue

        if month in low and str(year) in low:

            if side == "before" and re.match(r"^\d+\.", f):
                out.append(f)

            if side == "after" and ".1." in f:
                out.append(f)

    return out


# ============================
# MONTH BUTTONS
# ============================
def make_month_buttons(active):
    return [
        dbc.Button(
            m.capitalize(),
            id={"type":"self-month-btn","month":m},
            size="sm",
            color="success" if m==active else "secondary",
            className="me-1 mb-2",
            n_clicks=0
        )
        for m in MONTHS
    ]


# ============================
# BUILD PANELS
# ============================
def build_panels(dept, model, month, year):

    folder = get_self_folder(dept, model)

    panels = []

    # existing files for view
    before_imgs = list_images_for_month(dept, model, month, year, "before")
    after_imgs  = list_images_for_month(dept, model, month, year, "after")

    for i in range(1, 11):

        # determine existing names
        bname = f"{i}.{month}{year}.jpg"
        aname = f"{i}.1.{month}{year}.jpg"

        left = dbc.Col([

            html.Div("Before Upload", className="fw-semibold"),

            dcc.Upload(
                id={"type":"before-upload","index":i},
                disabled=True,
                children=html.Div("Drag & Drop or Click"),
                style={
                    "width":"100%",
                    "height":"90px",
                    "border":"2px dashed #666",
                    "textAlign":"center"
                }
            ),

            html.Div(
                id={"type":"self-before-preview","index":i},
                children=preview_img(os.path.join(folder, bname))
                if os.path.exists(os.path.join(folder,bname)) else None
            ),

        ], md=6)


        right = dbc.Col([

            html.Div("After Upload", className="fw-semibold"),

            dcc.Upload(
                id={"type":"after-upload","index":i},
                disabled=True,
                children=html.Div("Drag & Drop or Click"),
                style={
                    "width":"100%",
                    "height":"90px",
                    "border":"2px dashed #28a745",
                    "textAlign":"center"
                }
            ),

            html.Div(
                id={"type":"self-after-preview","index":i},
                children=preview_img(os.path.join(folder, aname))
                if os.path.exists(os.path.join(folder,aname)) else None
            ),

        ], md=6)

        panels.append(dbc.Row([left,right], className="mb-4"))

    return panels



# ============================
# LAYOUT
# ============================
layout = dbc.Container([

    html.Div([
        html.Div("Self Audit", className="page-title"),
        html.Div("USER Only Upload – Controlled Access", className="page-subtitle"),
    ], className="mb-3"),

    dbc.Card(
        dbc.CardBody([

            dbc.Row([
                dbc.Col([
                    html.Label("Department"),
                    dcc.Dropdown(
                        id="self_dd_department",
                        options=[],
                        placeholder="Select Department"
                    )
                ], md=4),

                dbc.Col([
                    html.Label("Model Area"),
                    dcc.Dropdown(
                        id="self_dd_model",
                        options=[],
                        placeholder="Select Model"
                    )
                ], md=4),

                dbc.Col([
                    html.Label(" "),
                    dbc.Button(
                        "Show",
                        id="self_btn_show",
                        color="primary",
                        className="action-btn w-100"
                    )
                ], md=3),
            ]),

            html.Div(className="soft-divider"),

            dbc.Row([
                dbc.Col([
                    html.Label("Year"),
                    dcc.Dropdown(
                        id="self_dd_year",
                        options=[{"label": y, "value": y} for y in year_options],
                        value=current_year,   
                        clearable=False
                    )
                ], md=3),

                dbc.Col([
                    html.Label(" "),
                    dbc.Button(
                        "Unlock Selected Month",
                        id="self_common_unlock",
                        className="unlock-btn"
                    )
                ], md=4),
            ]),

        ]),
        className="control-card"
    ),

    html.Div(id="self-month-buttons", className="month-strip"),
    html.H5(id="active_month_label", className="text-primary mt-3"),
    html.Div(id="self_images_container"),

    # PASSWORD MODAL
    dbc.Modal(
    [
        dbc.ModalHeader(dbc.ModalTitle("Upload Authorization")),
        dbc.ModalBody([
            dbc.Input(id="upload_password", type="password",
                      placeholder="Password"),
            html.Div(id="pwd_error", className="text-danger mt-2")
        ]),
        dbc.ModalFooter(
            dbc.Button("Verify", id="btn_verify_pwd", color="primary")
        ),
    ],
    id="self_pwd_modal",
    backdrop="static",
    centered=True,
    is_open=False
    ),

    dcc.Store(id="pwd_ok", data=False),
    dcc.Store(
        id="selected_month",
        storage_type="session"   # 🔥 THIS IS THE KEY
    ),

    dcc.Store(id="session_context", data={"dept":None,"model":None}),

])



@callback(
    Output({"type": "before-upload", "index": ALL}, "disabled"),
    Output({"type": "after-upload", "index": ALL}, "disabled"),
    Input("pwd_ok", "data"),
    prevent_initial_call=True
)
def enable_all_uploads(pwd_ok):
    if pwd_ok:
        return [False] * 10, [False] * 10
    raise dash.exceptions.PreventUpdate


# 1) Departments loader
@callback(
    Output("self-month-buttons","children"),
    Input("selected_month","data"),
)
def update_month_buttons(active_month):

    if not active_month:
        active_month = datetime.now().strftime("%B").lower()

    return make_month_buttons(active_month)

@callback(
    Output("active_month_label","children"),
    Input("selected_month","data"),
    State("self_dd_year","value"),
)
def show_month(month, year):
    if not month:
        return ""
    return f"Showing images for {month.capitalize()} {year}"

@callback(
    Output("self_dd_department","options"),
    Input("self_dd_department","id")
)
def load_departments(_):
    df = read_dt_fresh()
    depts = sorted(d for d in df["department"].unique() if d)
    return [{"label": d, "value": d} for d in depts]


@callback(
    Output("session_context","data"),
    Input("self_btn_show","n_clicks"),
    State("self_dd_department","value"),
    State("self_dd_model","value"),
    prevent_initial_call=True
)
def store_context(_, dept, model):
    return {"dept":dept, "model":model}

# 2) Models filter
@callback(
    Output("self_dd_model","options"),
    Input("self_dd_department","value"),
)
def filter_models_by_department(dept):

    if not dept:
        return []

    df = read_dt_fresh()
    rows = df[df["department"] == str(dept)]

    models = sorted(m for m in rows["model"].unique() if m)

    return [{"label": m, "value": m} for m in sorted(models)]




@callback(
    Output("self_pwd_modal","is_open"),
    Output("pwd_ok","data"),
    Output("pwd_error","children"),

    Input("self_common_unlock","n_clicks"),
    Input("btn_verify_pwd","n_clicks"),

    State("pwd_ok","data"),
    State("upload_password","value"),
    State("self_dd_department","value"),
    State("self_dd_model","value"),

    prevent_initial_call=True
)
def handle_unlock_and_verify(
    unlock_click,
    verify_click,
    pwd_ok,
    entered_pwd,
    dept,
    model
):
    trigger = ctx.triggered_id

    # 🔓 USER CLICKED UNLOCK BUTTON
    if trigger == "self_common_unlock":
        if pwd_ok:
            return False, pwd_ok, ""
        return True, False, ""

    # ✅ USER CLICKED VERIFY BUTTON
    if trigger == "btn_verify_pwd":

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



@callback(
    Output("selected_month","data"),
    Input({"type":"self-month-btn","month":ALL},"n_clicks"),
    Input("self_btn_show","n_clicks"),
    State("selected_month","data"),
    prevent_initial_call=True
)
def set_selected_month(_, show_clicks, current_month):
    trigger = ctx.triggered_id

    if isinstance(trigger, dict):
        return trigger["month"]

    if trigger == "self_btn_show":
        return current_month or datetime.now().strftime("%B").lower()

    return current_month

@callback(
    Output("self_images_container","children"),
    Input("selected_month","data"),
    State("self_dd_department","value"),
    State("self_dd_model","value"),
    State("self_dd_year","value"),
    prevent_initial_call=True
)

def month_public_view(selected_month, dept, model, year):


    if not selected_month or not dept or not model:
        raise dash.exceptions.PreventUpdate  

    return build_panels(
        dept=dept,
        model=model,
        month=selected_month,
        year=year
    )


# 7) INSTANT SAVE + REPLACE
# ============================
@callback(
    Output({"type":"self-before-preview","index":MATCH},"children", allow_duplicate=True),
    Input({"type":"before-upload","index":MATCH},"contents"),
    State("self_dd_department","value"),
    State("self_dd_model","value"),
    State("self_dd_year","value"),
    State("selected_month","data"),
    prevent_initial_call=True
)
def instant_before(contents, dept, model, year, month):

    if not contents or not month:
        raise dash.exceptions.PreventUpdate

    i = ctx.triggered_id["index"]
    save_name = f"{i}.{month}{year}.jpg"

    folder = get_self_folder(dept, model)

    _, cstring = contents.split(",")
    binary = base64.b64decode(cstring)

    with open(os.path.join(folder, save_name), "wb") as f:
        f.write(binary)

    return html.Div(
        html.Img(src=f"data:image/jpg;base64,{cstring}", style=IMG_STYLE),
        style=IMG_FRAME_STYLE
    )




@callback(
    Output({"type":"self-after-preview","index":MATCH},"children", allow_duplicate=True),
    Input({"type":"after-upload","index":MATCH},"contents"),
    State("self_dd_department","value"),
    State("self_dd_model","value"),
    State("self_dd_year","value"),
    State("selected_month","data"),
    prevent_initial_call=True
)
def instant_after(contents, dept, model, year,month):

    
    i=ctx.triggered_id["index"]

    save_name = f"{i}.1.{month}{year}.jpg"

    folder=get_self_folder(dept, model)
    path=os.path.join(folder,save_name)

    _, cstring = contents.split(",")
    binary=base64.b64decode(cstring)

    with open(path,"wb") as f:
        f.write(binary)

    return html.Div(
        html.Img(src=f"data:image/jpg;base64,{cstring}", style=IMG_STYLE),
        style=IMG_FRAME_STYLE
    )


