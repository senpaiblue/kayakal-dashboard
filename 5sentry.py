# dash_tab_5s_upload.py
# Dash tab for 5S image upload
# - Month dropdown: 12 months from current month (handles year rollover)
# - Loads departments / 5S Model Areas / team leader from ./assets/5s/DT.xlsx
# - Add new Department + 5S Model Area + Team Leader to the Excel (no duplicate dept+model)
# - Upload images (drag & drop), save to ./assets/5s/<Department>/<ModelArea>/
# - Filenames: <index><monthname><year>.<ext> e.g. 1june2025.jpg

import os
from pathlib import Path
import re
import calendar
import datetime as dt
import base64

import pandas as pd
from dash import Dash, dcc, html, Input, Output, State
import dash

# ---------- CONFIG ----------
ASSETS_FOLDER = Path("./assets/5s")
EXCEL_PATH = ASSETS_FOLDER / "DT.xlsx"
DEPT_COL = "department"
MODEL_COL = "model"
LEADER_COL = "leader"

ASSETS_FOLDER.mkdir(parents=True, exist_ok=True)

# Ensure excel exists with required columns
def ensure_excel():
    if not EXCEL_PATH.exists():
        df = pd.DataFrame(columns=[DEPT_COL, MODEL_COL, LEADER_COL])
        EXCEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        df.to_excel(EXCEL_PATH, index=False)

ensure_excel()

# Month dropdown: 12 months starting from current month (handles year change)
def get_month_options():
    today = dt.date.today()
    opts = []
    for i in range(12):
        # month number with rollover
        month_num = ((today.month - 1 + i) % 12) + 1
        year = today.year + ((today.month - 1 + i) // 12)
        label = f"{calendar.month_name[month_num]} {year}"
        value = f"{month_num}-{year}"
        opts.append({"label": label, "value": value})
    return opts

# Load unique departments from excel
def load_departments():
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception:
        return []
    if DEPT_COL in df.columns:
        return sorted(df[DEPT_COL].dropna().astype(str).unique())
    return []

# Load model areas for given department
def load_model_areas(dept):
    if not dept:
        return []
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception:
        return []
    if DEPT_COL not in df.columns or MODEL_COL not in df.columns:
        return []
    mask = df[DEPT_COL].astype(str).str.strip().fillna("") == str(dept).strip()
    return sorted(df.loc[mask, MODEL_COL].dropna().astype(str).unique())

# Create Dash app
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

app.layout = html.Div([
    html.H2("5S — Image Upload"),
    html.Div(style={"display": "flex", "gap": "24px"}, children=[
        # LEFT: Upload panel
        html.Div(style={"flex": "1", "padding":"16px", "border":"1px solid #e0e0e0", "borderRadius":"8px",
                        "boxShadow":"0 2px 6px rgba(0,0,0,0.03)"}, children=[
            html.H4("Upload Images"),
            html.Label("Select Month (required)"),
            dcc.Dropdown(id="month-dropdown", options=get_month_options(), placeholder="Select month...", clearable=False),
            html.Br(),
            html.Label("Select Department (required)"),
            dcc.Dropdown(id="department-dropdown",
                         options=[{"label": d, "value": d} for d in load_departments()],
                         placeholder="Select department...", clearable=False),
            html.Br(),
            html.Label("Select 5S Model Area (required)"),
            dcc.Dropdown(id="model-dropdown", options=[], placeholder="Select 5S Model Area...", clearable=False),
            html.Br(),
            html.Label("Select one or more images (drag & drop)"),
            dcc.Upload(
                id="image-uploader",
                children=html.Div(["Drag & Drop or ", html.A("Select Files")]),
                multiple=True,
                style={
                    "width": "100%", "height": "130px", "lineHeight": "130px",
                    "borderWidth": "2px", "borderStyle": "dashed", "borderRadius": "8px",
                    "textAlign": "center", "marginBottom": "8px"
                }
            ),
            html.Button("Upload", id="upload-button", n_clicks=0, disabled=True,
                        style={"border":"1px solid #555","padding":"8px 16px","borderRadius":"6px","cursor":"pointer"}),
            html.Div(id="upload-output", style={"marginTop":"12px"})
        ]),

        # RIGHT: Add new Department / Model Area / Team Leader
        html.Div(style={"flex":"0.8", "padding":"16px", "border":"1px solid #e0e0e0", "borderRadius":"8px",
                        "boxShadow":"0 2px 6px rgba(0,0,0,0.03)"}, children=[
            html.H4("Add New Department / 5S Model Area / Team Leader"),
            html.Label("Department Name"),
            dcc.Input(id="new-dept", type="text", placeholder="Enter department name", style={"width":"100%","padding":"8px","borderRadius":"4px","border":"1px solid #ccc"}),
            html.Br(), html.Br(),
            html.Label("5S Model Area"),
            dcc.Input(id="new-model", type="text", placeholder="Enter model area", style={"width":"100%","padding":"8px","borderRadius":"4px","border":"1px solid #ccc"}),
            html.Br(), html.Br(),
            html.Label("Team Leader"),
            dcc.Input(id="new-leader", type="text", placeholder="Enter team leader name", style={"width":"100%","padding":"8px","borderRadius":"4px","border":"1px solid #ccc"}),
            html.Br(), html.Br(),
            html.Button("Save Department + Model Area + Leader", id="save-dept-model", n_clicks=0,
                        style={"border":"1px solid #555","padding":"8px 12px","borderRadius":"6px","cursor":"pointer"}),
            html.Div(id="save-output", style={"marginTop":"12px"}),
            html.Hr(),
            html.Div(id="existing-preview")
        ])
    ])
], style={"fontFamily":"Arial, Helvetica, sans-serif", "maxWidth":"1100px", "margin":"18px auto"})

# Enable upload button only when all required fields filled and files present
@app.callback(
    Output("upload-button", "disabled"),
    Input("month-dropdown", "value"),
    Input("department-dropdown", "value"),
    Input("model-dropdown", "value"),
    Input("image-uploader", "contents")
)
def toggle_upload_disabled(month_val, dept, model, contents):
    if month_val and dept and model and contents:
        return False
    return True

# Populate model dropdown based on department
@app.callback(
    Output("model-dropdown", "options"),
    Input("department-dropdown", "value")
)
def update_model_options(dept):
    areas = load_model_areas(dept)
    return [{"label": a, "value": a} for a in areas]

# Handle uploads
@app.callback(
    Output("upload-output", "children"),
    Input("upload-button", "n_clicks"),
    State("month-dropdown", "value"),
    State("department-dropdown", "value"),
    State("model-dropdown", "value"),
    State("image-uploader", "contents"),
    State("image-uploader", "filename")
)
def handle_upload(n_clicks, month_val, dept, model, contents, filenames):
    if not n_clicks:
        return ""
    if not (month_val and dept and model and contents):
        return html.Div("Error: All fields mandatory and at least one file must be selected.", style={"color":"red"})

    # parse month value like "6-2026"
    try:
        m_str, y_str = month_val.split("-")
        month_num = int(m_str)
        year_num = int(y_str)
        month_name = calendar.month_name[month_num].lower()
    except Exception as e:
        return html.Div(f"Invalid month selection: {e}", style={"color":"red"})

    # Folder: ./assets/5s/<Department>/<ModelArea>/
    folder = ASSETS_FOLDER / str(dept).strip() / str(model).strip()
    folder.mkdir(parents=True, exist_ok=True)

    # Determine start index by scanning existing files that match pattern like ^(\d+)<monthname><year>
    existing_indices = []
    for f in folder.iterdir():
        if f.is_file():
            stem = f.stem.lower()
            # find an integer at start followed by monthname+year somewhere
            m = re.search(r"^(\d+).*" + re.escape(month_name) + re.escape(str(year_num)), stem)
            if m:
                try:
                    existing_indices.append(int(m.group(1)))
                except Exception:
                    pass
    current_index = max(existing_indices) + 1 if existing_indices else 1

    saved = []
    # contents is list of strings like "data:<mime>;base64,AAAA..."
    for idx, content in enumerate(contents):
        try:
            header, b64 = content.split(",", 1)
        except ValueError:
            continue
        # extension from original filename if available
        fname = None
        try:
            fname = filenames[idx]
        except Exception:
            fname = None
        ext = Path(fname).suffix if fname else ".jpg"
        if not ext:
            ext = ".jpg"
        save_name = f"{current_index}{month_name}{year_num}{ext}"
        save_path = folder / save_name
        # decode and write
        try:
            with open(save_path, "wb") as fh:
                fh.write(base64.b64decode(b64))
            saved.append(save_name)
            current_index += 1
        except Exception as e:
            # skip faulty file but continue
            continue

    if not saved:
        return html.Div("No files saved (something went wrong).", style={"color":"orange"})

    return html.Div([
        html.Div(f"Saved {len(saved)} file(s) to {folder}"),
        html.Ul([html.Li(s) for s in saved])
    ])

# Save new Department + ModelArea + Team Leader (prevents duplicate dept+model)
@app.callback(
    Output("save-output", "children"),
    Output("department-dropdown", "options"),
    Output("existing-preview", "children"),
    Input("save-dept-model", "n_clicks"),
    State("new-dept", "value"),
    State("new-model", "value"),
    State("new-leader", "value")
)
def save_dept_model(n_clicks, new_dept, new_model, new_leader):
    # initial load: show existing departments
    if not n_clicks:
        depts = load_departments()
        preview = html.Div([html.H5("Existing Departments"), html.Ul([html.Li(d) for d in depts])])
        return dash.no_update, [{"label": d, "value": d} for d in depts], preview

    # validations
    if not new_dept or not new_model or not new_leader:
        return html.Div("Please fill all fields.", style={"color":"red"}), dash.no_update, dash.no_update

    new_dept = str(new_dept).strip()
    new_model = str(new_model).strip()
    new_leader = str(new_leader).strip()

    # load df and check duplicates
    try:
        df = pd.read_excel(EXCEL_PATH)
    except Exception:
        df = pd.DataFrame(columns=[DEPT_COL, MODEL_COL, LEADER_COL])

    # ensure required columns exist
    for c in [DEPT_COL, MODEL_COL, LEADER_COL]:
        if c not in df.columns:
            df[c] = ""

    dup_mask = (df[DEPT_COL].astype(str).str.strip() == new_dept) & (df[MODEL_COL].astype(str).str.strip() == new_model)
    if dup_mask.any():
        return html.Div("This Department + Model Area already exists!", style={"color":"orange"}), dash.no_update, dash.no_update

    # append row and save
    df = pd.concat([df, pd.DataFrame([{DEPT_COL: new_dept, MODEL_COL: new_model, LEADER_COL: new_leader}])], ignore_index=True)
    try:
        df.to_excel(EXCEL_PATH, index=False)
    except Exception as e:
        return html.Div(f"Failed to save to Excel: {e}", style={"color":"red"}), dash.no_update, dash.no_update

    depts = load_departments()
    preview = html.Div([html.H5("Existing Departments"), html.Ul([html.Li(d) for d in depts])])
    return html.Div("Saved successfully!", style={"color":"green"}), [{"label": d, "value": d} for d in depts], preview


if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=1111)
