# dash_tab_5s_user_full.py
# Front-end user page: unlimited images per month (Option B)
# Save as ./dash_tab_5s_user_full.py and import into your main Dash app or run standalone.

import os
import re
import base64
import calendar
import datetime as dt
from pathlib import Path
import dash
import pandas as pd
from dash import Dash, dcc, html, Input, Output, State, ALL, MATCH, ctx

# -------- CONFIG ----------
ASSETS_FOLDER = Path("./assets/5s")
EXCEL_PATH = ASSETS_FOLDER / "DT.xlsx"
DEPT_COL = "department name"
AREA_COL = "model area"
LEAD_COL = "team leader"

# UI sizes
IMG_WIDTH = 300
IMG_HEIGHT = 200

# Ensure assets folder exists
ASSETS_FOLDER.mkdir(parents=True, exist_ok=True)
if not EXCEL_PATH.exists():
    # create empty DT.xlsx if missing
    pd.DataFrame(columns=[DEPT_COL, AREA_COL, LEAD_COL]).to_excel(EXCEL_PATH, index=False)
    print("DEBUG: Created empty DT.xlsx at", EXCEL_PATH)

# Helper functions ------------------------------------------------------------
def read_master_df():
    try:
        df = pd.read_excel(EXCEL_PATH)
        # normalize column names if old names exist
        cols = [c.strip().lower() for c in df.columns]
        return df
    except Exception as e:
        print("ERROR: reading DT.xlsx:", e)
        return pd.DataFrame(columns=[DEPT_COL, AREA_COL, LEAD_COL])

def list_departments():
    df = read_master_df()
    if DEPT_COL in df.columns:
        return sorted(df[DEPT_COL].dropna().astype(str).unique())
    return []

def list_model_areas(dept):
    df = read_master_df()
    if dept is None or dept == "" or DEPT_COL not in df.columns or AREA_COL not in df.columns:
        return []
    mask = df[DEPT_COL].astype(str).str.strip() == str(dept).strip()
    return sorted(df.loc[mask, AREA_COL].dropna().astype(str).unique())

def leader_for(dept, area):
    df = read_master_df()
    try:
        row = df[(df[DEPT_COL].astype(str).str.strip() == str(dept).strip()) &
                 (df[AREA_COL].astype(str).str.strip() == str(area).strip())]
        if not row.empty and LEAD_COL in row.columns:
            return str(row[LEAD_COL].iloc[0])
    except Exception as e:
        print("DEBUG: leader_for error", e)
    return ""

# parse filenames like "1december2025.jpg" or "1.1december2025.jpg"
FILENAME_RE = re.compile(r"^(\d+)(?:\.(\d+))?([a-z]+)(\d{4})", flags=re.IGNORECASE)

def parse_filename(fname):
    stem = Path(fname).stem.lower()
    m = FILENAME_RE.match(stem)
    if not m:
        return None
    base_idx = int(m.group(1))
    version = int(m.group(2)) if m.group(2) else 0
    monthname = m.group(3)
    year = int(m.group(4))
    return {"base": base_idx, "version": version, "month": monthname, "year": year}

def files_for_month_year(folder, monthname, year):
    """Return list of filenames in folder that contain monthname and year in pattern used."""
    if not Path(folder).exists():
        print("DEBUG: folder does not exist:", folder)
        return []
    out = []
    for f in sorted(os.listdir(folder)):
        if not f.lower().endswith((".jpg", ".jpeg", ".png", ".gif", ".bmp")):
            continue
        parsed = parse_filename(f)
        if parsed and parsed["month"].lower() == monthname.lower() and parsed["year"] == year:
            out.append(f)
    return out

def available_years_for_month(folder, monthname):
    """Scan filenames for the month and return sorted list of years found."""
    years = set()
    if not Path(folder).exists():
        return []
    for f in os.listdir(folder):
        parsed = parse_filename(f)
        if parsed and parsed["month"].lower() == monthname.lower():
            years.add(parsed["year"])
    return sorted(years)

def next_base_index(folder, monthname, year):
    """Return next base integer to use for new images for this month/year."""
    if not Path(folder).exists():
        return 1
    base_idxs = []
    for f in os.listdir(folder):
        parsed = parse_filename(f)
        if parsed and parsed["month"].lower() == monthname.lower() and parsed["year"] == year:
            base_idxs.append(parsed["base"])
    return max(base_idxs) + 1 if base_idxs else 1

def next_version_for_base(folder, base, monthname, year):
    """Return next version integer for a given base index."""
    vers = []
    if not Path(folder).exists():
        return 1
    for f in os.listdir(folder):
        parsed = parse_filename(f)
        if parsed and parsed["month"].lower() == monthname.lower() and parsed["year"] == year and parsed["base"] == base:
            vers.append(parsed["version"])
    return max(vers) + 1 if vers else 1

# App layout -------------------------------------------------------------------
app = Dash(__name__, suppress_callback_exceptions=True)
server = app.server

MONTHS = [calendar.month_name[i] for i in range(1,13)]
CURRENT_MONTH_IDX = dt.datetime.now().month - 1
CURRENT_YEAR = dt.datetime.now().year

app.layout = html.Div([
    html.H2("5S Model Area View & Upload", style={"textAlign":"center"}),
    html.Div([
        html.Div([
            html.Label("Select Department"),
            dcc.Dropdown(id="dept-dd", options=[{"label":d,"value":d} for d in list_departments()], placeholder="Select Department"),
            html.Br(),
            html.Label("Select Model Area"),
            dcc.Dropdown(id="area-dd", options=[], placeholder="Select Model Area"),
            html.Br(),
            html.Div(id="leader-box", style={"fontWeight":"600", "marginTop":"8px"}),
        ], style={"width":"60%", "display":"inline-block", "verticalAlign":"top"}),

        html.Div([
            html.Div("DEBUG LOG (terminal also prints):", style={"fontWeight":"600"}),
            html.Pre(id="debug-box", style={"whiteSpace":"pre-wrap","height":"120px","overflow":"auto","border":"1px solid #ccc","padding":"8px","background":"#fafafa"})
        ], style={"width":"38%", "display":"inline-block", "verticalAlign":"top", "paddingLeft":"12px"})
    ], style={"maxWidth":"1100px","margin":"auto"}),

    # Month buttons row
    html.Div(id="months-row", style={"maxWidth":"1100px","margin":"20px auto","display":"flex","gap":"8px","flexWrap":"wrap"}),

    html.Hr(),

    # Image display grid: left column existing images, right column upload/replace
    html.Div(id="image-area", style={"maxWidth":"1100px","margin":"auto","display":"flex","gap":"30px"}),

    # hidden store to keep selected month index and year
    dcc.Store(id="selected-month"),  # will hold dict: {"month_idx":int,"year":int,"month_name":str}
    # trigger to force refresh
    dcc.Store(id="refresh-trigger", data=0)
], style={"fontFamily":"Arial, Helvetica, sans-serif", "padding":"20px"})

# Helper to log debug to both terminal and debug-box
def append_debug(msg):
    print("DEBUG:", msg)
    return msg + "\n"

# ------------------ Callbacks ------------------

# Populate areas when department selected


# Show leader and render month buttons when area selected
@app.callback(
    Output("leader-box", "children"),
    Output("months-row", "children"),
    Input("area-dd", "value"),
    State("dept-dd", "value")
)
def on_area_change(area, dept):
    if not dept or not area:
        return "", []
    leader = leader_for(dept, area)
    # Build month buttons; highlight current month
    buttons = []
    for idx, m in enumerate(MONTHS):
        style = {
            "padding":"8px 12px", "border":"2px solid #333", "borderRadius":"6px", "cursor":"pointer",
            "backgroundColor":"#f2f6ff" if idx == CURRENT_MONTH_IDX else "white"
        }
        buttons.append(html.Button(m, id={"type":"month-btn","index":idx}, n_clicks=0, style=style))
    leader_text = f"Team Leader - {leader}" if leader else "Team Leader - N/A"
    return leader_text, buttons

# Determine which month button clicked -> set selected-month store (month_idx and best year)
@app.callback(
    Output("selected-month", "data"),
    Output("debug-box", "children"),
    Input({"type":"month-btn","index":ALL}, "n_clicks"),
    State("dept-dd", "value"),
    State("area-dd", "value"),
    State("selected-month", "data"),
    State("debug-box", "children")
)
def on_month_clicked(n_clicks_list, dept, area, prev_selected, prev_debug):
    debug_text = prev_debug or ""
    if not dept or not area:
        debug_text += append_debug("WARN: department/area missing when clicking month.")
        return dash.no_update, debug_text

    # determine which button was triggered
    triggered = ctx.triggered_id
    # fallback: find last clicked index > 0
    month_idx = None
    if triggered and isinstance(triggered, dict) and triggered.get("type") == "month-btn":
        month_idx = int(triggered.get("index"))
    else:
        for i, c in enumerate(n_clicks_list):
            if c:
                month_idx = i
        # if none clicked, default to current month
    if month_idx is None:
        month_idx = CURRENT_MONTH_IDX

    month_name = MONTHS[month_idx].lower()
    folder = ASSETS_FOLDER / str(dept) / str(area)
    debug_text += append_debug(f"INFO: Month '{MONTHS[month_idx]}' selected for Dept='{dept}', Area='{area}'. Scanning folder: {folder}")

    # determine which year to use
    years = available_years_for_month(folder, month_name)
    chosen_year = None
    if CURRENT_YEAR in years:
        chosen_year = CURRENT_YEAR
        debug_text += append_debug(f"INFO: Found images for current year {CURRENT_YEAR}. Using that.")
    elif years:
        chosen_year = max(years)
        debug_text += append_debug(f"INFO: No images for current year. Using most recent year found: {chosen_year}.")
    else:
        # default to current year if none exist (will show empty)
        chosen_year = CURRENT_YEAR
        debug_text += append_debug("INFO: No images found for that month; defaulting to current year (may be empty).")

    return {"month_idx": month_idx, "month_name": month_name, "year": chosen_year}, debug_text

# Render images + upload UI based on selected-month, department, area, and refresh-trigger
@app.callback(
    Output("image-area", "children"),
    Output("debug-box", "children"),
    Input("selected-month", "data"),
    Input("dept-dd", "value"),
    Input("area-dd", "value"),
    Input("refresh-trigger", "data"),
    State("debug-box", "children")
)
def render_image_area(selected, dept, area, refresh, prev_debug):
    debug_text = prev_debug or ""
    if not selected or not dept or not area:
        debug_text += append_debug("INFO: Waiting for selection (dept/area/month).")
        return html.Div("Please select Department, Model Area and Month."), debug_text

    month_idx = int(selected.get("month_idx"))
    month_name = selected.get("month_name")
    year = int(selected.get("year"))
    folder = ASSETS_FOLDER / str(dept) / str(area)
    debug_text += append_debug(f"INFO: Rendering images for {MONTHS[month_idx]} {year} from folder {folder}")

    # Ensure folder exists (create for admin later)
    folder.mkdir(parents=True, exist_ok=True)

    # List files matching month+year
    file_list = files_for_month_year(folder, month_name, year)
    debug_text += append_debug(f"INFO: Found {len(file_list)} files for {month_name}{year}.")

    # Left column: show all existing images (sorted by base index, then version)
    imgs_left = []
    # sort files by base index then version
    def sort_key(fname):
        p = parse_filename(fname)
        if p:
            return (p["base"], p["version"])
        return (9999, 0)

    file_list_sorted = sorted(file_list, key=sort_key)
    for fname in file_list_sorted:
        src = f"/assets/5s/{dept}/{area}/{fname}"
        img_div = html.Div([
            html.Img(src=src, style={"width": f"{IMG_WIDTH}px", "height": f"{IMG_HEIGHT}px", "border": "3px solid #222", "objectFit": "cover"}),
            html.Div(fname, style={"textAlign":"center", "marginTop":"6px"})
        ], style={"marginBottom":"18px"})
        imgs_left.append(img_div)

    left_column = html.Div(imgs_left, style={"flex":"1"})

    # Right column: for each existing base index show upload replace area under that image,
    # and at bottom show "Upload New Images" area.
    right_elements = []
    # Determine unique base indices to show replace slots (in original order)
    bases = []
    for fname in file_list_sorted:
        p = parse_filename(fname)
        if p and p["base"] not in bases:
            bases.append(p["base"])

    # For each base, show the latest image (max version) and a replace upload
    for base in bases:
        # find latest file for this base
        same_base = [f for f in file_list_sorted if parse_filename(f)["base"] == base]
        last = sorted(same_base, key=lambda x: parse_filename(x)["version"], reverse=True)[0]
        src = f"/assets/5s/{dept}/{area}/{last}"
        replace_block = html.Div([
            html.Img(src=src, style={"width": f"{IMG_WIDTH}px", "height": f"{IMG_HEIGHT}px", "border": "3px solid #222", "objectFit": "cover"}),
            html.Div(last, style={"textAlign":"center", "marginTop":"6px"}),
            html.Div([
                dcc.Upload(
                    id={"type":"replace-upload","base": base},
                    children=html.Button("Replace Image (upload)"),
                    multiple=False,
                    style={"marginTop":"8px"}
                )
            ], style={"marginTop":"6px"})
        ], style={"marginBottom":"20px"})
        right_elements.append(replace_block)

    # Upload new images block (appends as new base indices)
    new_upload_block = html.Div([
        html.H4(f"Upload New Image(s) for {MONTHS[month_idx]} {year}"),
        dcc.Upload(
            id="new-upload",
            children=html.Div(["Drag & Drop or ", html.A("Select Files")]),
            multiple=True,
            style={"width":"100%", "height":"120px", "lineHeight":"120px", "borderWidth":"2px", "borderStyle":"dashed", "borderRadius":"8px", "textAlign":"center"}
        )
    ], style={"marginTop":"30px"})

    right_column = html.Div(right_elements + [new_upload_block], style={"flex":"1"})

    return html.Div([left_column, right_column], style={"display":"flex","gap":"30px"}), debug_text

# Handle replacing a specific base image (creates a versioned filename e.g., 1.1december2025.jpg)
@app.callback(
    Output("refresh-trigger", "data"),
    Output("debug-box", "children"),
    Input({"type":"replace-upload","base":ALL}, "contents"),
    State({"type":"replace-upload","base":ALL}, "filename"),
    State({"type":"replace-upload","base":ALL}, "id"),
    State("dept-dd", "value"),
    State("area-dd", "value"),
    State("selected-month", "data"),
    State("debug-box", "children"),
    prevent_initial_call=True
)
def handle_replacement(contents_list, filenames, ids, dept, area, selected, prev_debug):
    debug_text = prev_debug or ""
    if not selected or not dept or not area:
        debug_text += append_debug("WARN: Replacement attempted without full selection.")
        return dash.no_update, debug_text

    folder = ASSETS_FOLDER / str(dept) / str(area)
    monthname = selected["month_name"]
    year = int(selected["year"])

    # iterate through inputs; find which one has content
    for i, content in enumerate(contents_list):
        if content:
            ident = ids[i]  # dict with 'type' and 'base'
            base = ident.get("base")
            fname = filenames[i] if filenames and i < len(filenames) else None
            debug_text += append_debug(f"INFO: Replacement upload for base={base}, filename={fname}")
            try:
                header, b64 = content.split(",",1)
            except Exception as e:
                debug_text += append_debug(f"ERROR: bad content for replacement: {e}")
                continue

            # get extension from provided filename or default to .jpg
            ext = Path(fname).suffix if fname else ".jpg"
            if not ext:
                ext = ".jpg"

            # compute next version for this base
            ver = next_version_for_base(folder, int(base), monthname, year)
            new_name = f"{base}.{ver}{monthname}{year}{ext}"
            save_path = folder / new_name
            try:
                with open(save_path, "wb") as fh:
                    fh.write(base64.b64decode(b64))
                debug_text += append_debug(f"INFO: Saved replacement as {save_path}")
            except Exception as e:
                debug_text += append_debug(f"ERROR: Could not save replacement {save_path}: {e}")
    # bump refresh store value to force refresh of image area
    try:
        new_val = int(dt.datetime.now().timestamp())
    except:
        new_val = 1
    return new_val, debug_text

# Handle uploading new images (append as new base indexes)
@app.callback(
    Output("refresh-trigger", "data"),
    Output("debug-box", "children"),
    Input("new-upload", "contents"),
    State("new-upload", "filename"),
    State("dept-dd", "value"),
    State("area-dd", "value"),
    State("selected-month", "data"),
    State("debug-box", "children"),
    prevent_initial_call=True
)
def handle_new_upload(contents, filenames, dept, area, selected, prev_debug):
    debug_text = prev_debug or ""
    if not contents:
        return dash.no_update, debug_text
    if not dept or not area or not selected:
        debug_text += append_debug("ERROR: Missing selection while uploading new images.")
        return dash.no_update, debug_text

    folder = ASSETS_FOLDER / str(dept) / str(area)
    monthname = selected["month_name"]
    year = int(selected["year"])
    folder.mkdir(parents=True, exist_ok=True)

    debug_text += append_debug(f"INFO: Uploading {len(contents)} new file(s) to {folder} for {monthname}{year}.")

    for i, content in enumerate(contents):
        try:
            header, b64 = content.split(",",1)
        except Exception as e:
            debug_text += append_debug(f"ERROR: invalid content for new-upload idx {i}: {e}")
            continue
        fname = filenames[i] if filenames and i < len(filenames) else f"image_{i}.jpg"
        ext = Path(fname).suffix if fname else ".jpg"
        if not ext:
            ext = ".jpg"

        new_base = next_base_index(folder, monthname, year)
        new_name = f"{new_base}{monthname}{year}{ext}"
        save_path = folder / new_name
        try:
            with open(save_path, "wb") as fh:
                fh.write(base64.b64decode(b64))
            debug_text += append_debug(f"INFO: Saved new image {save_path}")
        except Exception as e:
            debug_text += append_debug(f"ERROR: Could not save new image {save_path}: {e}")
            continue

    # force refresh
    try:
        new_val = int(dt.datetime.now().timestamp())
    except:
        new_val = 1
    return new_val, debug_text

# ------------------ Run server (if run directly) ------------------
if __name__ == "__main__":
    print("DEBUG: Starting Dash app. Ensure you run this from project root so ./assets path is correct.")
    app.run(debug=True)
