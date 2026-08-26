import dash
import os
from dash import html, dcc, Input, Output, State, ctx, ALL
import pandas as pd
import base64
import io
import csv
import time
from PIL import Image
import dash_bootstrap_components as dbc
import urllib.parse
from datetime import datetime

from apps.progress import read_pending_csv
from apps.red_tag_museum import read_rt_pending_csv
from apps.greenery import read_greenery_pending_csv
from apps.area_master_admin import read_area_master_for, get_exec_team_person

# Register callbacks on the live Dash app (index.py uses app from app.py).
# @dash.callback can miss outputs in callback_map on some setups; see k5_trends.py.
from app import app as _app

dash.register_page(__name__, path="/tec")


# ======================================================
# LOAD CSV
# ======================================================

dep_df = pd.read_csv("./assets/k5/dep.csv", encoding="cp1252")
et_df = pd.read_csv("./Data/execution_team.csv", encoding="utf-8")

TEC_ZONES = list(dict.fromkeys(dep_df["DIC ZONE NAME"].dropna()))

# Build HOD → Area label mapping from execution_team.csv
_hod_to_area = {}
for _, row in et_df.iterrows():
    et_name = str(row.get("Execution Team", "")).strip()
    area = str(row.get("Area", "")).strip()
    if et_name and area:
        _hod_to_area[et_name] = area


# ======================================================
# LAYOUT
# ======================================================

layout = html.Div([

    # 🔥 SESSION STORES (GLOBAL across pages)
    # dcc.Store(id="selected-zone", storage_type="session"),
    # dcc.Store(id="selected-department", storage_type="session"),

    dcc.Location(id="redirect"),
    dcc.Interval(id="k5-admin-badge-interval", interval=5000),

    html.Div(id="k5-breadcrumb", style={"padding": "10px", "fontWeight": "bold", "color": "#555"}),

    html.H3("TEC Zone & Department Selection",
            style={"textAlign": "center"}),

    # ── Trends button ────────────────────────────────────────
    html.Div(
        dcc.Link(
            html.Button(
                "📊  View Submission Trends",
                style={
                    "background": "linear-gradient(135deg,#1a73e8,#0d47a1)",
                    "color": "white",
                    "border": "none",
                    "padding": "10px 22px",
                    "borderRadius": "8px",
                    "cursor": "pointer",
                    "fontWeight": "600",
                    "fontSize": "14px",
                    "boxShadow": "0 4px 12px rgba(26,115,232,0.35)",
                    "transition": "all 0.2s",
                },
                id="k5-view-trends-btn",
            ),
            href="/k5-trends",
        ),
        style={"textAlign": "center", "marginBottom": "18px"}
    ),


    # ==============================
    # ZONE BUTTONS
    # ==============================
    html.Div(
        id="zone-row",
        children=[
            html.Button(
                zone,
                id={"type": "zone-btn", "zone": zone},
                n_clicks=0
            )
            for zone in TEC_ZONES
        ],
        style={"textAlign": "center"}
    ),


    # ==============================
    # Department container
    # ==============================
    html.Div(
        id="department-row",
        style={"textAlign": "center", "marginTop": "15px"}
    ),


    html.Hr(),


    # ==============================
    # MENU
    # ==============================
    html.Div(
        [
            dcc.Link(html.Button("Progress"), href="/progress"),
            dcc.Link(html.Button("Greenery"), href="/greenery"),
            dcc.Link(html.Button("Remarks"), href="/remarks"),
            dcc.Link(html.Button("Value Credited"), href="/valuecredited"),
            dcc.Link(html.Button("Red Tag Museum"), href="/red_tag_museum"),
            dcc.Link(html.Button("Projects Identified"), href="/projects-identified-display"),

            html.Div([
                html.Button(
                    "Admin",
                    id="admin-btn",
                    style={"display": "none"},
                ),
                html.Div(
                    id="admin-modal",
                    style={
                        "display": "none",
                        "position": "absolute",
                        "top": "100%",
                        "right": "0",
                        "backgroundColor": "white",
                        "padding": "15px",
                        "border": "1px solid #ccc",
                        "borderRadius": "8px",
                        "boxShadow": "0 4px 8px rgba(0,0,0,0.1)",
                        "zIndex": "1000",
                        "minWidth": "250px",
                        "marginTop": "10px"
                    },
                    children=[
                        dcc.Input(id="admin-user", placeholder="Username", style={"display": "block", "margin": "0 auto 10px", "width": "100%"}),
                        dcc.Input(id="admin-pass", type="password", placeholder="Password", style={"display": "block", "margin": "0 auto 10px", "width": "100%"}),
                        html.Button("Login", id="admin-login-btn", style={"width": "100%"}),
                        html.Div(id="admin-msg", style={"color": "red", "marginTop": "5px"})
                    ]
                )
            ], style={"position": "relative"}),
        ],
        id="k5-tabs-container",
        style={
            "display": "none",
            "justifyContent": "center",
            "gap": "25px"
        }
    ),


    html.Div(id="k5-upcoming-events-section", style={"marginTop": "30px", "marginBottom": "20px", "display": "flex", "justifyContent": "center"}),
    html.Div(id="k5-dept-map-section", style={"textAlign": "center", "marginTop": "40px", "marginBottom": "20px"}),
    html.Div(id="k5-area-master-preview-section", style={"marginTop": "20px", "marginBottom": "40px", "maxWidth": "900px", "margin": "0 auto"}),



])


# ======================================================
# MASTER CALLBACK (zone + dept + highlight)
# ======================================================

@dash.callback(
    Output("department-row", "children"),
    Output("zone-row", "children"),
    Output("selected-zone", "data"),
    Output("selected-department", "data"),

    Input({"type": "zone-btn", "zone": ALL}, "n_clicks"),
    Input({"type": "dept-btn", "dept": ALL}, "n_clicks"),

    State("selected-zone", "data")
)
def handle_all(zone_clicks, dept_clicks, current_zone):

    triggered = ctx.triggered_id

    # -------------------
    # default styles
    # -------------------
    def zone_buttons(active=None):
        buttons = []
        for z in TEC_ZONES:
            style = {
                "margin": "6px",
                "padding": "10px 18px",
                "border": "1px solid black"
            }

            if z == active:
                style["backgroundColor"] = "#cfe8ff"  # highlight

            buttons.append(
                html.Button(z, id={"type": "zone-btn", "zone": z}, style=style)
            )
        return buttons


    def get_dept_labels(zone_name):
        labels = []
        if not zone_name:
            return labels
        zone_rows = dep_df[dep_df["DIC ZONE NAME"] == zone_name]
        from collections import OrderedDict
        hod_groups = OrderedDict()
        for _, r in zone_rows.iterrows():
            hod = str(r["HOD"]).strip()
            dept = str(r["Department"]).strip()
            hod_groups.setdefault(hod, []).append(dept)

        for hod, dept_list in hod_groups.items():
            if len(dept_list) > 1:
                label = _hod_to_area.get(hod, ", ".join(dept_list))
            else:
                label = dept_list[0]
            if label not in labels:
                labels.append(label)
        return labels

    def build_dept_buttons(zone_name, active_dept=None):
        buttons = []
        labels = get_dept_labels(zone_name)
        for label in labels:
            style = {"margin": "4px"}
            if label == active_dept:
                style["backgroundColor"] = "#cfe8ff"
                style["border"] = "1px solid black"
                
            buttons.append(
                html.Button(
                    label,
                    id={"type": "dept-btn", "dept": label},
                    style=style,
                )
            )
        return buttons


    if not triggered:
        return [], zone_buttons(), dash.no_update, dash.no_update


    # -------------------
    # ZONE CLICK
    # -------------------
    if triggered["type"] == "zone-btn":
        zone = triggered["zone"]
        labels = get_dept_labels(zone)
        
        if len(labels) == 1:
            only_dept = labels[0]
            dept_buttons = build_dept_buttons(zone, active_dept=only_dept)
            return dept_buttons, zone_buttons(zone), zone, only_dept
            
        dept_buttons = build_dept_buttons(zone)
        return dept_buttons, zone_buttons(zone), zone, dash.no_update


    # -------------------
    # DEPT CLICK
    # -------------------
    if triggered["type"] == "dept-btn":
        dept = triggered["dept"]
        dept_buttons = build_dept_buttons(current_zone, dept)
        return dept_buttons, dash.no_update, dash.no_update, dept



# ======================================================
# SHOW ADMIN BUTTON & MENU TABS & BREADCRUMB
# ======================================================

@dash.callback(
    Output("k5-breadcrumb", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data")
)
def update_k5_breadcrumb(zone, dept):
    if not zone:
        return ""
    if not dept:
        return f"Location: {zone}"
    return f"Location: {zone} > {dept}"

@dash.callback(
    Output("k5-tabs-container", "style"),
    Input("selected-department", "data")
)
def toggle_k5_tabs_visibility(dept):
    if dept:
        return {
            "display": "flex",
            "justifyContent": "center",
            "gap": "25px"
        }
    return {"display": "none"}


@dash.callback(
    Output("admin-btn", "style"),
    Input("selected-department", "data")
)
def show_admin(dept):
    return {"display": "inline-block", "position": "relative"} if dept else {"display": "none"}

# ======================================================
# BADGE UPDATE
# ======================================================
@dash.callback(
    Output("admin-btn", "children"),
    Input("k5-admin-badge-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data")
)
def update_admin_badge(_, zone, dept):
    if not zone or not dept:
        return "Admin"

    total = 0
    # Progress
    for r in read_pending_csv():
        if r.get("zone") == zone and r.get("dept") == dept and r.get("status") == "pending":
            total += 1
            
    # Red Tag
    for r in read_rt_pending_csv():
        if r.get("zone") == zone and r.get("dept") == dept and r.get("status") == "pending":
            total += 1
            
    # Greenery
    for r in read_greenery_pending_csv():
        if r.get("zone") == zone and r.get("dept") == dept and r.get("status") == "pending":
            total += 1
            
    # Value Credited
    vc_path = "./Data/value_credited_pending.csv"
    if os.path.isfile(vc_path) and os.path.getsize(vc_path) > 0:
        with open(vc_path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                if r.get("zone") == zone and r.get("dept") == dept and r.get("status") == "pending":
                    total += 1
            
    if total > 0:
        badge = html.Span(
            str(total),
            style={
                "backgroundColor": "red",
                "color": "white",
                "borderRadius": "50%",
                "padding": "2px 6px",
                "fontSize": "12px",
                "fontWeight": "bold",
                "position": "absolute",
                "top": "-10px",
                "right": "-10px",
                "boxShadow": "0px 2px 4px rgba(0,0,0,0.3)"
            }
        )
        return ["Admin", badge]
    
    return "Admin"



# ======================================================
# DEPARTMENT MAP UPLOAD & PREVIEW / EVENTS UI
# ======================================================

@dash.callback(
    Output("k5-upcoming-events-section", "children"),
    Input("selected-department", "data")
)
def render_k5_upcoming_events(dept):
    if not dept:
        return html.Div()
        
    safe_area = "".join(c for c in dept if c.isalnum() or c in " _-").strip()
    area_path = os.path.join("assets", "upcoming_events", safe_area)
    
    if not os.path.exists(area_path) or not os.path.isdir(area_path):
        return html.Div()
        
    events = []
    for fname in os.listdir(area_path):
        fpath = os.path.join(area_path, fname)
        if os.path.isfile(fpath):
            mtime = os.path.getmtime(fpath)
            dt = datetime.fromtimestamp(mtime)
            events.append({
                "filename": fname,
                "date": dt,
                "url": f"/assets/upcoming_events/{safe_area}/{urllib.parse.quote(fname)}"
            })
            
    if not events:
        return html.Div()
        
    events.sort(key=lambda x: x["date"], reverse=True)
    
    cards = []
    for i, ev in enumerate(events):
        idx = f"{i+1:02d}"
        title = ev["filename"].rsplit('.', 1)[0]
        if len(title) > 30:
            title = title[:30] + "..."
        date_str = ev["date"].strftime("%d %b %Y")
        
        card = html.A(
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
                    "alignItems": "center", "boxShadow": "0 4px 6px rgba(0,0,0,0.1)", "minWidth": "280px",
                    "maxWidth": "350px", "cursor": "pointer"
                }
            ),
            href=ev["url"],
            target="_blank",
            style={"textDecoration": "none"}
        )
        cards.append(card)

    return html.Div(
        [
            html.Div(
                "DOCUMENTS",
                style={
                    "writingMode": "vertical-rl", "transform": "rotate(180deg)", "fontWeight": "bold",
                    "fontSize": "13px", "letterSpacing": "2px", "color": "#334", "marginRight": "10px",
                    "paddingTop": "10px"
                }
            ),
            html.Div(
                cards,
                style={"display": "flex", "gap": "15px", "overflowX": "auto"}
            )
        ],
        style={
            "display": "flex", "background": "#eef2f5", "padding": "20px", "borderRadius": "10px",
            "marginBottom": "10px", "maxWidth": "900px", "width": "100%", "alignItems": "flex-start",
            "boxSizing": "border-box"
        }
    )

@dash.callback(
    Output("k5-dept-map-section", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data")
)
def render_dept_map(zone, dept):
    if not zone or not dept:
        return html.Div()

    folder = os.path.join("./assets/K5", zone, dept)
    map_path = os.path.join(folder, "map.png")

    if os.path.isfile(map_path):
        with open(map_path, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        img_src = f"data:image/png;base64,{encoded}"

        return html.Div([
            html.H5(f"Layout Map: {dept}", className="mb-3"),
            html.Div(
                html.Img(src=img_src, style={"maxWidth": "100%", "maxHeight": "1200px", "border": "2px solid #ccc", "borderRadius": "8px"}),
                style={"marginBottom": "15px", "textAlign": "center"}
            )
        ])
    else:
        return html.Div([
            html.H5(f"Layout Map for {dept} not yet uploaded.", className="mb-3 text-muted")
        ])


# ======================================================
# AREA MASTER READ-ONLY PREVIEW
# ======================================================

@dash.callback(
    Output("k5-area-master-preview-section", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data")
)
def render_k5_area_master_preview(zone, dept):
    if not zone or not dept:
        return html.Div()

    existing = read_area_master_for(zone, dept)
    exec_person = get_exec_team_person(zone, dept)
    from apps.progress import get_progress_folder, parse_files, load_text_map
    progress_folder = get_progress_folder(zone, dept)
    progress_rows = parse_files(progress_folder)
    progress_text_map = load_text_map(zone, dept)

    from apps.greenery import get_greenery_folder, parse_files as parse_greenery_files, load_text_map as load_greenery_text_map
    greenery_folder = get_greenery_folder(zone, dept)
    greenery_rows = parse_greenery_files(greenery_folder)
    greenery_text_map = load_greenery_text_map(zone, dept)

    stats_by_ac = {}
    grand_ba = 0
    grand_aa = 0

    # 1. Progress approved files on disk
    for r in progress_rows:
        bef = r["before"]
        aft = r["after"]
        ac_key = ""
        if bef and bef in progress_text_map:
            ac_key = str(progress_text_map[bef].get("area_code", "")).strip()
        elif aft and aft in progress_text_map:
            ac_key = str(progress_text_map[aft].get("area_code", "")).strip()
            
        if not ac_key and dept == "RMHS Base mix and Energy Yard":
            ac_key = "0"
            
        if ac_key:
            if ac_key not in stats_by_ac:
                stats_by_ac[ac_key] = {
                    "before_pending": 0, "before_approved": 0,
                    "after_pending": 0, "after_approved": 0,
                }
            if bef:
                stats_by_ac[ac_key]["before_approved"] += 1
                grand_ba += 1
            if aft:
                stats_by_ac[ac_key]["after_approved"] += 1
                grand_aa += 1
        else:
            if bef:
                grand_ba += 1
            if aft:
                grand_aa += 1

    # 2. Greenery approved files on disk
    for r in greenery_rows:
        bef = r["before"]
        aft = r["after"]
        ac_key = ""
        if bef and bef in greenery_text_map:
            ac_key = str(greenery_text_map[bef].get("area_code", "")).strip()
        elif aft and aft in greenery_text_map:
            ac_key = str(greenery_text_map[aft].get("area_code", "")).strip()
            
        if not ac_key and dept == "RMHS Base mix and Energy Yard":
            ac_key = "0"
            
        if ac_key:
            if ac_key not in stats_by_ac:
                stats_by_ac[ac_key] = {
                    "before_pending": 0, "before_approved": 0,
                    "after_pending": 0, "after_approved": 0,
                }
            if bef:
                stats_by_ac[ac_key]["before_approved"] += 1
                grand_ba += 1
            if aft:
                stats_by_ac[ac_key]["after_approved"] += 1
                grand_aa += 1
        else:
            if bef:
                grand_ba += 1
            if aft:
                grand_aa += 1

    # Build sets of approved files physically on disk to avoid double-counting
    approved_before_files = set()
    approved_after_files = set()
    for r in progress_rows:
        if r.get("before"):
            approved_before_files.add(r["before"])
        if r.get("after"):
            approved_after_files.add(r["after"])
    for r in greenery_rows:
        if r.get("before"):
            approved_before_files.add(r["before"])
        if r.get("after"):
            approved_after_files.add(r["after"])

    # Now load PENDING images from CSV
    grand_bp = 0
    grand_ap = 0

    for p in ["Data/pending_approvals.csv", "Data/greenery_pending.csv"]:
        if os.path.exists(p):
            with open(p, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("zone") == zone and row.get("dept") == dept:
                        st = row.get("status", "")
                        if st == "pending":
                            ac_key = row.get("area_code", "").strip()
                            if not ac_key and row.get("dept") == "RMHS Base mix and Energy Yard":
                                ac_key = "0"
                                
                            has_before = bool(row.get("before_file", "").strip())
                            has_after = bool(row.get("after_file", "").strip())
                            
                            # Safeguard against double-counting files already approved on disk
                            before_fn = row.get("before_file", "").strip()
                            after_fn = row.get("after_file", "").strip()
                            if has_before and before_fn in approved_before_files:
                                has_before = False
                            if has_after and after_fn in approved_after_files:
                                has_after = False
                                
                            is_simultaneous = bool(row.get("location_name", "").strip())
                            
                            bp_val = 0
                            ap_val = 0
                            if has_before and (is_simultaneous or not has_after):
                                bp_val = 1
                            if has_after:
                                ap_val = 1
                                
                            grand_bp += bp_val
                            grand_ap += ap_val
                            
                            if ac_key:
                                if ac_key not in stats_by_ac:
                                    stats_by_ac[ac_key] = {
                                        "before_pending": 0, "before_approved": 0,
                                        "after_pending": 0, "after_approved": 0,
                                    }
                                stats_by_ac[ac_key]["before_pending"] += bp_val
                                stats_by_ac[ac_key]["after_pending"] += ap_val
    
    header = dbc.Row(
        [
            dbc.Col(html.B("Area Code"), width=1),
            dbc.Col(html.B("Location Name"), width=2),
            dbc.Col(html.B("Sub Location Name"), width=2),
            dbc.Col(html.B("Responsible Person"), width=2),
            dbc.Col(html.B("Before Pending"), width=1),
            dbc.Col(html.B("Before Approved"), width=1),
            dbc.Col(html.B("After Pending"), width=1),
            dbc.Col(html.B("After Approved"), width=1),
        ],
        className="py-2 bg-light border-bottom text-center flex-nowrap",
        style={"position": "sticky", "top": "0", "zIndex": "1", "minWidth": "1400px"}
    )

    rows = [header]
    for ac in range(0, 111):
        rec = existing.get(ac, {})
        loc = rec.get("location_name", "")
        subloc = rec.get("sub_location_name", "")
        person = rec.get("responsible_person", "")
        
        if ac == 0 and not loc and not subloc and not person:
            loc = dept
            subloc = dept
            person = exec_person

        ac_stats = stats_by_ac.get(str(ac), {})
        bp = ac_stats.get("before_pending", 0)
        ba = ac_stats.get("before_approved", 0)
        ap = ac_stats.get("after_pending", 0)
        aa = ac_stats.get("after_approved", 0)

        if not loc and not subloc and not person:
            continue

        rows.append(
            dbc.Row(
                [
                    dbc.Col(html.Span(str(ac), className="fw-bold"), width=1, className="text-center"),
                    dbc.Col(html.Span(loc if loc else "-"), width=2, className="text-center"),
                    dbc.Col(html.Span(subloc if subloc else "-"), width=2, className="text-center"),
                    dbc.Col(html.Span(person if person else "-"), width=2, className="text-center"),
                    dbc.Col(html.Span(str(bp), className="text-danger fw-bold"), width=1, className="text-center"),
                    dbc.Col(html.Span(str(ba), className="text-success fw-bold"), width=1, className="text-center"),
                    dbc.Col(html.Span(str(ap), className="text-danger fw-bold"), width=1, className="text-center"),
                    dbc.Col(html.Span(str(aa), className="text-success fw-bold"), width=1, className="text-center"),
                ],
                className="py-1 border-bottom align-items-center flex-nowrap",
                style={"minWidth": "1400px"}
            )
        )

    rows.append(
        dbc.Row(
            [
                dbc.Col(html.Span("Grand Total", className="fw-bold"), width=7, className="text-end pe-3"),
                dbc.Col(html.Span(str(grand_bp), className="text-danger fw-bold"), width=1, className="text-center"),
                dbc.Col(html.Span(str(grand_ba), className="text-success fw-bold"), width=1, className="text-center"),
                dbc.Col(html.Span(str(grand_ap), className="text-danger fw-bold"), width=1, className="text-center"),
                dbc.Col(html.Span(str(grand_aa), className="text-success fw-bold"), width=1, className="text-center"),
            ],
            className="py-2 bg-light border-top align-items-center flex-nowrap",
            style={"minWidth": "1400px", "position": "sticky", "bottom": "0", "zIndex": "1"}
        )
    )

    return html.Div([
        html.H5(f"Area Master Data — {dept}", className="mb-3 text-center"),
        html.Div(
            rows,
            style={
                "maxHeight": "400px",
                "overflowY": "auto",
                "overflowX": "auto",
                "border": "1px solid #ddd",
                "borderRadius": "5px"
            }
        )
    ])



# ======================================================
# OPEN LOGIN MODAL
# ======================================================

@dash.callback(
    Output("admin-modal", "style"),
    Input("admin-btn", "n_clicks"),
    State("admin-modal", "style"),
    prevent_initial_call=True
)
def open_modal(_, current_style):
    new_style = current_style.copy()
    new_style["display"] = "block"
    return new_style



# ======================================================
# LOGIN CHECK + REDIRECT
# ======================================================

@dash.callback(
    Output("redirect", "href"),
    Output("admin-msg", "children"),

    Input("admin-login-btn", "n_clicks"),

    State("admin-user", "value"),
    State("admin-pass", "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),

    prevent_initial_call=True
)
def admin_login(_, user, pwd, zone, dept):
    """Validate login against execution_team.csv credentials.

    Flow:
      1. Match dept (Area name) directly to execution_team.csv Area column.
      2. Validate username/password against the stored credentials.
    """
    if not user or not pwd:
        return dash.no_update, "Enter username and password"

    # Look up the execution team member for this area
    et_path = os.path.join("Data", "execution_team.csv")
    try:
        et_local = pd.read_csv(et_path, keep_default_na=False)
    except Exception:
        return dash.no_update, "Credential file not found"

    match = et_local[et_local["Area"].str.strip() == dept]
    if match.empty:
        # Fall back to finding HOD via dep.csv for non-merged dept names
        row = dep_df[
            (dep_df["DIC ZONE NAME"] == zone) &
            (dep_df["Department"] == dept)
        ]
        if row.empty:
            return dash.no_update, "Invalid zone/department"
        hod_name = str(row.iloc[0]["HOD"]).strip()
        match = et_local[et_local["Execution Team"].str.strip() == hod_name]
        if match.empty:
            return dash.no_update, "No credentials set for this area"

    stored_user = str(match.iloc[0].get("Username", "")).strip()
    stored_pass = str(match.iloc[0].get("Password", "")).strip()

    if not stored_user or not stored_pass:
        return dash.no_update, "Credentials not yet created — contact admin"

    # Validate
    if user.strip() == stored_user and pwd == stored_pass:
        return "/progress-admin", ""

    return dash.no_update, "Invalid credentials"
