import dash
import os
import csv
import time as _time
import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, Input, Output, State, callback_context
import dash_bootstrap_components as dbc
from datetime import datetime, timedelta

# Use the live app instance directly so every callback is registered into
# app.callback_map at module-import time. This avoids the GLOBAL_CALLBACK_MAP
# transfer step used by `@dash.callback`, which can occasionally miss callbacks
# if a module is imported after `_setup_server` has already run.
from app import app as _app


# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_DEP_CSV = "./assets/K5/dep.csv"
_PENDING_CSV = "./Data/pending_approvals.csv"
_GREENERY_CSV = "./Data/greenery_pending.csv"

COLORS = [
    "#e63946", "#2a9d8f", "#e9c46a", "#264653",
    "#f4a261", "#457b9d", "#a8dadc", "#6a4c93",
    "#1982c4", "#8ac926", "#ff6b6b", "#48cae4",
]


def k5t_load_dep_csv():
    try:
        return pd.read_csv(_DEP_CSV, encoding="cp1252")
    except Exception:
        return pd.DataFrame(columns=["DIC ZONE NAME", "Department", "HOD"])


def k5t_get_zones():
    df = k5t_load_dep_csv()
    return list(dict.fromkeys(df["DIC ZONE NAME"].dropna()))


def k5t_get_grouped_depts_for_zone(zone):
    """Return an OrderedDict of {grouped_label: [individual_dept, ...]} for a zone.

    Mirrors the HOD-based grouping used in k5.py:
      - Departments that share the same HOD are merged under the 'Area' label
        from execution_team.csv (or a comma-joined fallback).
      - Solo departments keep their own name as the label.
    """
    from collections import OrderedDict
    dep_df = k5t_load_dep_csv()
    try:
        et_df = pd.read_csv("./Data/execution_team.csv", encoding="utf-8")
    except Exception:
        et_df = pd.DataFrame(columns=["Execution Team", "Area"])

    # Build HOD → Area label map
    hod_to_area = {}
    for _, row in et_df.iterrows():
        et_name = str(row.get("Execution Team", "")).strip()
        area = str(row.get("Area", "")).strip()
        if et_name and area:
            hod_to_area[et_name] = area

    zone_rows = dep_df[dep_df["DIC ZONE NAME"] == zone]
    hod_groups = OrderedDict()
    for _, r in zone_rows.iterrows():
        hod = str(r["HOD"]).strip()
        dept = str(r["Department"]).strip()
        hod_groups.setdefault(hod, []).append(dept)

    grouped = OrderedDict()
    for hod, dept_list in hod_groups.items():
        if len(dept_list) > 1:
            label = hod_to_area.get(hod, ", ".join(dept_list))
        else:
            label = dept_list[0]
        if label not in grouped:
            grouped[label] = []
        grouped[label].extend(dept_list)

    return grouped


def k5t_get_depts_for_zone(zone):
    """Return just the grouped label list (for backward compat)."""
    return list(k5t_get_grouped_depts_for_zone(zone).keys())



# ─────────────────────────────────────────────────────────────────────────────
# DISK ORPHAN SCANNER
# Images that exist on disk but have no corresponding CSV record are called
# "orphaned". They arise when a concurrent write_pending_csv() call overwrites
# a row that was being appended simultaneously. We scan the K5 assets folder
# and count any such images so totals stay accurate even if CSV records are lost.
# ─────────────────────────────────────────────────────────────────────────────

_K5_ASSETS = "./assets/K5"
_orphan_cache: dict = {"before": None, "after": None, "ts": 0.0}
_ORPHAN_CACHE_TTL = 60  # seconds – re-scan disk at most once per minute

_submissions_cache: dict = {
    "before": None,
    "before_ts": 0.0,
    "after": None,
    "after_ts": 0.0
}
_SUBMISSIONS_CACHE_TTL = 10.0  # seconds


def _k5t_compute_disk_orphans():
    """Scan K5 assets folder and return (orphan_before_df, orphan_after_df).

    An image is "orphaned" if its filename does not appear in either
    pending_approvals.csv or greenery_pending.csv.
    Both the main progress folder (approved images) and the pending subfolder
    are scanned so that records lost from either approved or pending sections
    of the CSV are recovered.
    """
    csv_before_set: set = set()
    csv_after_set: set = set()
    for path in [_PENDING_CSV, _GREENERY_CSV]:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    bf = row.get("before_file", "").strip()
                    af = row.get("after_file", "").strip()
                    if bf:
                        csv_before_set.add(bf)
                    if af:
                        csv_after_set.add(af)
        except Exception:
            pass

    before_rows: list = []
    after_rows: list = []
    _empty = pd.DataFrame(columns=["zone", "dept", "date", "status", "file_name"])

    if not os.path.isdir(_K5_ASSETS):
        return _empty.copy(), _empty.copy()

    for zone_dir in os.listdir(_K5_ASSETS):
        zone_path = os.path.join(_K5_ASSETS, zone_dir)
        if not os.path.isdir(zone_path):
            continue
        for dept_dir in os.listdir(zone_path):
            # All orphaned images are images whose CSV record was lost during
            # a concurrent write — they are no longer visible in the operational
            # approval queue (HoD cannot see/act on them). To keep the Pending
            # bar reflecting only the real operational queue (matching the
            # Admin badge count), all orphans are bucketed as "approved" so
            # they still contribute to the all-time totals without inflating
            # the workflow Pending count.
            for scan_subdir, inferred_status in (
                (os.path.join(zone_path, dept_dir, "progress"), "approved"),
                (os.path.join(zone_path, dept_dir, "progress", "pending"), "approved"),
            ):
                if not os.path.isdir(scan_subdir):
                    continue
                for fname in os.listdir(scan_subdir):
                    if not fname.lower().endswith(".jpg"):
                        continue
                    parts = fname.split(".")
                    # Valid before: {idx}.{dt_str}.jpg  (3 parts)
                    # Valid after:  {idx}.1.{dt_str}.jpg (4 parts, parts[1]=="1")
                    if len(parts) not in (3, 4):
                        continue
                    try:
                        int(parts[0])
                    except ValueError:
                        continue
                    is_after = len(parts) == 4 and parts[1] == "1"
                    dt_str = parts[-2]
                    try:
                        dt = datetime.strptime(dt_str, "%d%m%Y%H%M%S")
                    except ValueError:
                        continue

                    record = {
                        "zone": zone_dir,
                        "dept": dept_dir,
                        "date": dt.date(),
                        "status": inferred_status,
                        "file_name": fname,
                    }
                    if is_after:
                        if fname not in csv_after_set:
                            after_rows.append(record)
                    else:
                        if fname not in csv_before_set:
                            before_rows.append(record)

    bdf = pd.DataFrame(before_rows) if before_rows else _empty.copy()
    adf = pd.DataFrame(after_rows) if after_rows else _empty.copy()
    return bdf, adf


def k5t_load_disk_orphans():
    """Return (orphan_before_df, orphan_after_df) using a short TTL cache."""
    now = _time.time()
    if (
        _orphan_cache["before"] is not None
        and (now - _orphan_cache["ts"]) < _ORPHAN_CACHE_TTL
    ):
        return _orphan_cache["before"], _orphan_cache["after"]
    bdf, adf = _k5t_compute_disk_orphans()
    _orphan_cache["before"] = bdf
    _orphan_cache["after"] = adf
    _orphan_cache["ts"] = now
    return bdf, adf


def k5t_load_submissions():
    """Load before image rows. Approved images are loaded from disk folders,
    while pending images are loaded from pending approvals CSVs.
    Columns returned: zone, dept, date (date only, no time), status, file_name.
    """
    now = _time.time()
    if (
        _submissions_cache["before"] is not None
        and (now - _submissions_cache["before_ts"]) < _SUBMISSIONS_CACHE_TTL
    ):
        return _submissions_cache["before"].copy()

    from apps.progress import get_progress_folder, parse_files as parse_prog_files
    from apps.greenery import get_greenery_folder, parse_files as parse_green_files

    rows = []

    # 1. Load approved images from disk folders
    zones = k5t_get_zones()
    for zone in zones:
        depts = k5t_get_depts_for_zone(zone)
        for dept in depts:
            # Progress approved
            prog_folder = get_progress_folder(zone, dept)
            if os.path.isdir(prog_folder):
                try:
                    for r in parse_prog_files(prog_folder):
                        if r.get("before"):
                            rows.append({
                                "zone": zone,
                                "dept": dept,
                                "date": r["dt"].date(),
                                "status": "approved",
                                "file_name": r["before"]
                            })
                except Exception:
                    pass

            # Greenery approved
            green_folder = get_greenery_folder(zone, dept)
            if os.path.isdir(green_folder):
                try:
                    for r in parse_green_files(green_folder):
                        if r.get("before"):
                            rows.append({
                                "zone": zone,
                                "dept": dept,
                                "date": r["dt"].date(),
                                "status": "approved",
                                "file_name": r["before"]
                            })
                except Exception:
                    pass

    # 2. Load pending images from CSV files
    for path in [_PENDING_CSV, _GREENERY_CSV]:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("status", "").strip()
                    if status != "pending":
                        continue

                    fn = row.get("before_file", "").strip()
                    if not fn:
                        continue

                    has_after = bool(row.get("after_file", "").strip())
                    is_simultaneous = bool(row.get("location_name", "").strip())

                    # Exact condition for before image
                    if not (is_simultaneous or not has_after):
                        continue

                    zone = row.get("zone", "").strip()
                    dept = row.get("dept", "").strip()
                    submitted = row.get("submitted_at", "").strip()
                    if not zone or not submitted:
                        continue
                    try:
                        dt = datetime.strptime(submitted, "%d-%m-%Y %H:%M:%S")
                        rows.append({
                            "zone": zone,
                            "dept": dept,
                            "date": dt.date(),
                            "status": "pending",
                            "file_name": fn,
                        })
                    except Exception:
                        pass
        except Exception:
            pass

    csv_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["zone", "dept", "date", "status", "file_name"])

    if not csv_df.empty:
        priority = {"approved": 0, "pending": 1}
        csv_df["priority"] = csv_df["status"].map(lambda s: priority.get(s, 2))
        csv_df = csv_df.sort_values("priority")
        csv_df = csv_df.drop_duplicates(subset=["zone", "dept", "file_name"], keep="first")
        csv_df = csv_df.drop(columns=["priority"])

    _submissions_cache["before"] = csv_df
    _submissions_cache["before_ts"] = now
    return csv_df.copy()


def k5t_load_after_submissions():
    """Load after image rows. Approved images are loaded from disk folders,
    while pending images are loaded from pending approvals CSVs.
    Columns returned: zone, dept, date (date only, no time), status, file_name.
    """
    now = _time.time()
    if (
        _submissions_cache["after"] is not None
        and (now - _submissions_cache["after_ts"]) < _SUBMISSIONS_CACHE_TTL
    ):
        return _submissions_cache["after"].copy()

    from apps.progress import get_progress_folder, parse_files as parse_prog_files
    from apps.greenery import get_greenery_folder, parse_files as parse_green_files

    rows = []

    # 1. Load approved images from disk folders
    zones = k5t_get_zones()
    for zone in zones:
        depts = k5t_get_depts_for_zone(zone)
        for dept in depts:
            # Progress approved
            prog_folder = get_progress_folder(zone, dept)
            if os.path.isdir(prog_folder):
                try:
                    for r in parse_prog_files(prog_folder):
                        if r.get("after"):
                            rows.append({
                                "zone": zone,
                                "dept": dept,
                                "date": r["dt"].date(),
                                "status": "approved",
                                "file_name": r["after"]
                            })
                except Exception:
                    pass

            # Greenery approved
            green_folder = get_greenery_folder(zone, dept)
            if os.path.isdir(green_folder):
                try:
                    for r in parse_green_files(green_folder):
                        if r.get("after"):
                            rows.append({
                                "zone": zone,
                                "dept": dept,
                                "date": r["dt"].date(),
                                "status": "approved",
                                "file_name": r["after"]
                            })
                except Exception:
                    pass

    # 2. Load pending images from CSV files
    for path in [_PENDING_CSV, _GREENERY_CSV]:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    status = row.get("status", "").strip()
                    if status != "pending":
                        continue

                    fn = row.get("after_file", "").strip()
                    if not fn:
                        continue

                    zone = row.get("zone", "").strip()
                    dept = row.get("dept", "").strip()
                    submitted = row.get("submitted_at", "").strip()
                    if not zone or not submitted:
                        continue
                    try:
                        dt = datetime.strptime(submitted, "%d-%m-%Y %H:%M:%S")
                        rows.append({
                            "zone": zone,
                            "dept": dept,
                            "date": dt.date(),
                            "status": "pending",
                            "file_name": fn,
                        })
                    except Exception:
                        pass
        except Exception:
            pass

    csv_df = pd.DataFrame(rows) if rows else pd.DataFrame(columns=["zone", "dept", "date", "status", "file_name"])

    if not csv_df.empty:
        priority = {"approved": 0, "pending": 1}
        csv_df["priority"] = csv_df["status"].map(lambda s: priority.get(s, 2))
        csv_df = csv_df.sort_values("priority")
        csv_df = csv_df.drop_duplicates(subset=["zone", "dept", "file_name"], keep="first")
        csv_df = csv_df.drop(columns=["priority"])

    _submissions_cache["after"] = csv_df
    _submissions_cache["after_ts"] = now
    return csv_df.copy()

def k5t_normalize_dept_name(dept_name):
    """Normalize department labels for safe cross-file matching."""
    return " ".join(str(dept_name).strip().split()).casefold()


def k5t_get_canonical_dept_mapping(zone):
    """Returns a dict mapping any individual department name (or clean lowercase version)
    to its canonical grouped label. Also maps the grouped labels to themselves.
    """
    # Expanded spelling mapping for standard verbose/shorthand variations
    SPELLING_MAP = {
        # HSM1
        "hot strip mill i": "HSM1",
        "hot strip mill 1": "HSM1",
        "hsm-1": "HSM1",
        "hsm1": "HSM1",
        
        # HSM2 & CTL
        "hsm2": "HSM2",
        "hsm-2": "HSM2",
        "hot strip mill ii": "HSM2",
        "hot strip mill 2": "HSM2",
        "ctl": "CTL",
        "hsm2 & ctl": "HSM2 & CTL",
        
        # HSM-3
        "hsm3": "HS-3",
        "hsm-3": "HSM-3",
        "hot strip mill 3": "HSM-3",
        
        # CRM1
        "crm1": "CRM1 & Service centres",
        "crm-1": "CRM1 & Service centres",
        "cold rolling mill i": "CRM1 & Service centres",
        "cold rolling mill 1": "CRM1 & Service centres",
        "crm1 & service centres": "CRM1 & Service centres",
        "crm1 & service centers": "CRM1 & Service centres",
        
        # CRM2
        "crm2": "CRM2",
        "crm-2": "CRM2",
        "cold rolling mill ii": "CRM2",
        "cold rolling mill 2": "CRM2",
        
        # WRM-2 & BRM-2
        "wrm2": "WRM-2",
        "wrm-2": "WRM-2",
        "wire rod mill ii": "WRM-2",
        "wire rod mill 2": "WRM-2",
        "brm2": "BRM-2",
        "brm-2": "BRM-2",
        "bar mill ii": "BRM-2",
        "bar mill 2": "BRM-2",
        "wrm-2 & brm-2": "WRM-2 & BRM-2",
        
        # WRM-1 & BRM-1
        "wrm1": "WRM-1",
        "wrm-1": "WRM-1",
        "wire rod mill i": "WRM-1",
        "wire rod mill 1": "WRM-1",
        "brm1": "BRM-1",
        "brm-1": "BRM-1",
        "bar rod mill i": "BRM-1",
        "bar rod mill 1": "BRM-1",
        "wrm-1 & brm-1": "WRM-1 & BRM-1",
    }

    mapping = {}
    grouped_map = k5t_get_grouped_depts_for_zone(zone)
    for label, member_depts in grouped_map.items():
        # Map the grouped label to itself
        mapping[label.strip()] = label
        mapping[label.strip().casefold()] = label
        # Map each individual member department to the grouped label
        for dept in member_depts:
            mapping[dept.strip()] = label
            mapping[dept.strip().casefold()] = label
            
    # Apply SPELLING_MAP resolution: for each verbose/shorthand variation, resolve it to its shorthand HOD member
    # and then resolve that HOD member to its final HOD canonical grouped label
    for spelling, resolved_shorthand in SPELLING_MAP.items():
        # Find if the resolved shorthand is mapped to a canonical HOD label in dep.csv for this zone
        if resolved_shorthand in mapping:
            canonical_label = mapping[resolved_shorthand]
            mapping[spelling] = canonical_label
            mapping[spelling.casefold()] = canonical_label
        elif resolved_shorthand.casefold() in mapping:
            canonical_label = mapping[resolved_shorthand.casefold()]
            mapping[spelling] = canonical_label
            mapping[spelling.casefold()] = canonical_label

    return mapping


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

layout = html.Div([
    dcc.Interval(id="k5t-refresh-interval", interval=30_000, n_intervals=0),

    # ── Top bar ──────────────────────────────────────────────────────────────
    html.Div([
        html.Div([
            html.H2("📊 Kayakalp Trends",
                    style={"margin": "0", "fontWeight": "700",
                           "background": "linear-gradient(90deg,#1a73e8,#0d47a1)",
                           "-webkit-background-clip": "text",
                           "-webkit-text-fill-color": "transparent"}),
            html.P("Live trends of before & after images submitted across all zones & departments",
                   style={"margin": "4px 0 0", "color": "#666", "fontSize": "14px"}),
        ]),
        html.Div([
            dcc.Link(
                html.Button(
                    "🏠  Go to K5 Upload Page",
                    style={
                        "background": "linear-gradient(135deg,#1a73e8,#0d47a1)",
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        "fontWeight": "600",
                        "fontSize": "14px",
                        "boxShadow": "0 4px 12px rgba(26,115,232,0.35)",
                        "transition": "all 0.2s",
                        "marginRight": "12px",
                    },
                    id="k5t-goto-upload-btn",
                ),
                href="/k5",
            ),
            dcc.Link(
                html.Button(
                    "🟥  Go to Red Tag Trends",
                    style={
                        "background": "linear-gradient(135deg,#e63946,#900c3f)",
                        "color": "white",
                        "border": "none",
                        "padding": "10px 20px",
                        "borderRadius": "8px",
                        "cursor": "pointer",
                        "fontWeight": "600",
                        "fontSize": "14px",
                        "boxShadow": "0 4px 12px rgba(230,57,70,0.35)",
                        "transition": "all 0.2s",
                    },
                    id="k5t-goto-rtt-btn",
                ),
                href="/red-tag-trends",
            )
        ]),
    ], style={
        "display": "flex",
        "alignItems": "center",
        "justifyContent": "space-between",
        "padding": "20px 28px 16px",
        "background": "white",
        "borderBottom": "1px solid #e8eaed",
        "position": "sticky", "top": "0", "zIndex": "100",
        "boxShadow": "0 2px 8px rgba(0,0,0,0.06)",
    }),

    html.Div([

        # ── KPI Row ──────────────────────────────────────────────────────────
        html.Div(id="k5t-kpi-row", style={"marginBottom": "28px"}),

        # ── Section 1: Zone-level trends ─────────────────────────────────────
        html.Div([
            html.H4("📈 Images Submitted — By Zone (All Time)",
                    style={"fontWeight": "700", "marginBottom": "12px", "color": "#1a1a2e"}),
            dcc.Graph(id="k5t-zone-bar-chart",
                      config={"displayModeBar": False},
                      style={"height": "380px"}),
        ], style={
            "background": "white", "borderRadius": "14px", "padding": "24px",
            "boxShadow": "0 2px 16px rgba(0,0,0,0.07)", "marginBottom": "24px",
        }),

        # ── Section 2: Zone daily trend (dotted) ─────────────────────────────
        html.Div([
            html.H4("📉 Zone Submission Trend — Past 30 Days (Before & After)",
                    style={"fontWeight": "700", "marginBottom": "16px", "color": "#1a1a2e"}),
            dbc.Tabs(id="k5t-zdot-zone-tabs", active_tab="__all__", className="mb-3"),
            dcc.Graph(id="k5t-zone-dot-chart",
                      config={"displayModeBar": False},
                      style={"height": "440px"}),
        ], style={
            "background": "white", "borderRadius": "14px", "padding": "24px",
            "boxShadow": "0 2px 16px rgba(0,0,0,0.07)", "marginBottom": "24px",
        }),

        # ── Section 3: Department tabs ────────────────────────────────────────
        html.Div([
            html.H4("🏭 Department-Level Submission Trends (Before & After)",
                    style={"fontWeight": "700", "marginBottom": "16px", "color": "#1a1a2e"}),

            dbc.Tabs(id="k5t-zone-tabs", active_tab=None, className="mb-3"),

            # Department bar chart for selected zone tab
            dcc.Graph(id="k5t-dept-bar-chart",
                      config={"displayModeBar": False}),

            html.Hr(style={"margin": "24px 0"}),

            # Area Code 0 Submission Trends
            html.H5("🏭 Area Code 0 Submission Trends by Department (Before & After)",
                    style={"fontWeight": "600", "marginBottom": "16px", "color": "#333"}),
            dcc.Graph(id="k5t-dept-bar-chart-ac0",
                      config={"displayModeBar": False}),

            html.Hr(style={"margin": "24px 0"}),

            # Department dotted trend for selected zone tab
            html.H5("Department Dotted Trend — Past 30 Days (Before & After)",
                    style={"fontWeight": "600", "marginBottom": "16px", "color": "#333"}),
            dbc.Tabs(id="k5t-ddot-dept-tabs", active_tab="__all__", className="mb-3"),
            dcc.Graph(id="k5t-dept-dot-chart",
                      config={"displayModeBar": False},
                      style={"height": "440px"}),

        ], style={
            "background": "white", "borderRadius": "14px", "padding": "24px",
            "boxShadow": "0 2px 16px rgba(0,0,0,0.07)", "marginBottom": "24px",
        }),

        # ── Section 4: Status breakdown ────────────────────────────────────────
        html.Div([
            html.H4("✅ Approval Status Breakdown — By Zone (Before & After)",
                    style={"fontWeight": "700", "marginBottom": "12px", "color": "#1a1a2e"}),
            dcc.Graph(id="k5t-status-before-chart",
                      config={"displayModeBar": False},
                      style={"height": "360px"}),
            dcc.Graph(id="k5t-status-after-chart",
                      config={"displayModeBar": False},
                      style={"height": "360px", "marginTop": "16px"}),
        ], style={
            "background": "white", "borderRadius": "14px", "padding": "24px",
            "boxShadow": "0 2px 16px rgba(0,0,0,0.07)", "marginBottom": "24px",
        }),

    ], style={"padding": "28px", "maxWidth": "1400px", "margin": "0 auto"}),

], style={"background": "#f4f7fc", "minHeight": "100vh", "fontFamily": "Inter, sans-serif"})


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: populate zone-level tabs (always)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-zone-tabs", "children"),
    Output("k5t-zone-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
    State("k5t-zone-tabs", "active_tab"),
)
def k5t_build_zone_tabs(_n, current_active):
    zones = k5t_get_zones()
    tabs = [dbc.Tab(label=z, tab_id=z) for z in zones]
    # If the user has already selected a valid tab, keep it active
    if current_active in zones:
        return tabs, current_active
    default = zones[0] if zones else None
    return tabs, default


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: KPI row
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-kpi-row", "children"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_kpis(_n):
    before_df = k5t_load_submissions()
    after_df = k5t_load_after_submissions()

    before_approved = len(before_df[before_df["status"] == "approved"]) if not before_df.empty else 0
    before_pending  = len(before_df[before_df["status"] == "pending"])  if not before_df.empty else 0
    after_approved  = len(after_df[after_df["status"] == "approved"])   if not after_df.empty else 0
    after_pending   = len(after_df[after_df["status"] == "pending"])    if not after_df.empty else 0

    today = datetime.now().date()
    today_before = len(before_df[before_df["date"] == today]) if not before_df.empty else 0
    today_after  = len(after_df[after_df["date"] == today])   if not after_df.empty else 0
    today_count  = today_before + today_after

    def kpi_card(value, label, color, icon):
        return html.Div([
            html.Div(icon, style={"fontSize": "28px", "marginBottom": "6px"}),
            html.Div(str(value), style={
                "fontSize": "32px", "fontWeight": "800", "color": color,
                "lineHeight": "1",
            }),
            html.Div(label, style={
                "fontSize": "13px", "color": "#666", "marginTop": "4px", "fontWeight": "500"
            }),
        ], style={
            "background": "white",
            "borderRadius": "14px",
            "padding": "20px 24px",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.07)",
            "flex": "1",
            "minWidth": "160px",
            "textAlign": "center",
            "borderTop": f"4px solid {color}",
        })

    return html.Div([
        kpi_card(before_approved, "Areas identified", "#2a9d8f", "✅"),
        kpi_card(before_pending,  "Areas identified approvalPending",  "#e9c46a", "⏳"),
        kpi_card(after_approved,  "Areas improved",  "#1a73e8", "🏁"),
        kpi_card(after_pending,   "Areas improved approval Pending",   "#e63946", "🔄"),
        kpi_card(today_count,     "Uploaded Today",          "#6a4c93", "🕐"),
    ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"})


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Zone-level bar chart (all-time totals)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-zone-bar-chart", "figure"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_zone_bar(_n):
    before_df = k5t_load_submissions()
    after_df  = k5t_load_after_submissions()

    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=380,
        annotations=[dict(
            text="No submission data available yet",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=16, color="#999"),
        )],
    )

    if before_df.empty and after_df.empty:
        return empty_fig

    all_zones = sorted(set(
        list(before_df["zone"].unique() if not before_df.empty else []) +
        list(after_df["zone"].unique()  if not after_df.empty  else [])
    ))

    before_counts_map = before_df.groupby("zone").size().to_dict() if not before_df.empty else {}
    after_counts_map  = after_df.groupby("zone").size().to_dict()  if not after_df.empty  else {}

    before_counts = [before_counts_map.get(z, 0) for z in all_zones]
    after_counts  = [after_counts_map.get(z, 0)  for z in all_zones]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Before Images",
        y=all_zones,
        x=before_counts,
        orientation="h",
        marker=dict(color="#1a73e8", opacity=0.88, line=dict(width=0)),
        text=before_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Before Images: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="After Images",
        y=all_zones,
        x=after_counts,
        orientation="h",
        marker=dict(color="#2a9d8f", opacity=0.88, line=dict(width=0)),
        text=after_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>After Images: %{x}<extra></extra>",
    ))

    fig.update_layout(
        title=dict(text="Total Images Submitted per Zone (Before vs After)", font=dict(size=14, color="#333")),
        xaxis_title="Number of Images",
        yaxis_title="",
        template="plotly_white",
        height=380,
        margin=dict(l=150, r=100, t=50, b=30),
        barmode="group",
        bargap=0.2,
        bargroupgap=0.05,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: populate zone dot tabs (All + each zone)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-zdot-zone-tabs", "children"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_build_zdot_tabs(_n):
    zones = k5t_get_zones()
    tabs = [dbc.Tab(label="All", tab_id="__all__")] + [
        dbc.Tab(label=z, tab_id=z) for z in zones
    ]
    return tabs


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Zone dotted trend (past 30 days, filtered by selected tab)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-zone-dot-chart", "figure"),
    Input("k5t-zdot-zone-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_zone_dot(active_tab, _n):
    before_df = k5t_load_submissions()
    after_df  = k5t_load_after_submissions()

    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=440,
        annotations=[dict(
            text="No submission data available yet",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=16, color="#999"),
        )],
    )

    if before_df.empty and after_df.empty:
        return empty_fig

    cutoff = (datetime.now() - timedelta(days=30)).date()
    selected_zone = active_tab if active_tab and active_tab != "__all__" else None

    def _filter30(df):
        if df.empty:
            return df
        d = df[df["date"] >= cutoff].copy()
        if selected_zone:
            d = d[d["zone"] == selected_zone]
        return d

    before30 = _filter30(before_df)
    after30  = _filter30(after_df)

    if before30.empty and after30.empty:
        empty_fig.update_layout(
            annotations=[dict(
                text="No submissions in the past 30 days",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=16, color="#999"),
            )]
        )
        return empty_fig

    all_zones_global = sorted(set(
        list(before_df["zone"].unique() if not before_df.empty else []) +
        list(after_df["zone"].unique()  if not after_df.empty  else [])
    ))
    color_map = {z: COLORS[i % len(COLORS)] for i, z in enumerate(all_zones_global)}

    title_suffix = selected_zone if selected_zone else "All Zones"
    fig = go.Figure()

    # Before traces (solid lines)
    if not before30.empty:
        daily_b = before30.groupby(["date", "zone"]).size().reset_index(name="count")
        for zone in sorted(daily_b["zone"].unique()):
            grp = daily_b[daily_b["zone"] == zone].sort_values("date")
            date_strs = [str(d) for d in grp["date"]]
            text_labels = [""] * len(grp)
            if len(grp) > 0:
                text_labels[-1] = f" <b>{zone} (B)</b>"
            fig.add_trace(go.Scatter(
                x=date_strs, y=grp["count"],
                mode="lines+markers+text",
                text=text_labels, textposition="top right",
                name=f"{zone} — Before",
                legendgroup=zone,
                marker=dict(color=color_map[zone], size=9, symbol="circle",
                            line=dict(width=1.5, color="white")),
                line=dict(color=color_map[zone], width=2.5, dash="solid"),
                hovertemplate=f"<b>{zone} — Before</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>",
            ))

    # After traces (dotted lines)
    if not after30.empty:
        daily_a = after30.groupby(["date", "zone"]).size().reset_index(name="count")
        for zone in sorted(daily_a["zone"].unique()):
            grp = daily_a[daily_a["zone"] == zone].sort_values("date")
            date_strs = [str(d) for d in grp["date"]]
            text_labels = [""] * len(grp)
            if len(grp) > 0:
                text_labels[-1] = f" <b>{zone} (A)</b>"
            fig.add_trace(go.Scatter(
                x=date_strs, y=grp["count"],
                mode="lines+markers+text",
                text=text_labels, textposition="top right",
                name=f"{zone} — After",
                legendgroup=zone,
                marker=dict(color=color_map[zone], size=9, symbol="diamond",
                            line=dict(width=1.5, color="white")),
                line=dict(color=color_map[zone], width=2.5, dash="dot"),
                hovertemplate=f"<b>{zone} — After</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>",
            ))

    fig.update_layout(
        title=dict(
            text=f"Daily Submissions — {title_suffix} — Past 30 Days (Solid=Before, Dotted=After)",
            font=dict(size=14, color="#333"),
        ),
        xaxis_title="Date",
        yaxis_title="Number of Images",
        template="plotly_white",
        height=440,
        margin=dict(l=20, r=160, t=50, b=50),
        showlegend=True,
        legend=dict(orientation="v", x=1.01, y=1),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Department bar chart (for selected zone tab)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-dept-bar-chart", "figure"),
    Input("k5t-zone-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_dept_bar(active_tab, _n):
    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=400,
        annotations=[dict(
            text="Select a zone tab above to see department trends",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=15, color="#999"),
        )],
    )

    if not active_tab:
        return empty_fig

    before_df = k5t_load_submissions()
    after_df  = k5t_load_after_submissions()

    zone_before = before_df[before_df["zone"] == active_tab] if not before_df.empty else pd.DataFrame()
    zone_after  = after_df[after_df["zone"] == active_tab]   if not after_df.empty  else pd.DataFrame()

    # Map department names in submissions to their HOD/canonical grouped labels to completely eliminate duplicates
    mapping = k5t_get_canonical_dept_mapping(active_tab)
    if not zone_before.empty:
        zone_before = zone_before.copy()
        zone_before["dept"] = zone_before["dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )
    if not zone_after.empty:
        zone_after = zone_after.copy()
        zone_after["dept"] = zone_after["dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )

    if zone_before.empty and zone_after.empty:
        empty_fig.update_layout(
            annotations=[dict(
                text=f"No images submitted for {active_tab} yet",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=15, color="#999"),
            )]
        )
        return empty_fig

    # Re-calculate deduplicated departments list
    all_depts = sorted(set(
        list(zone_before["dept"].unique() if not zone_before.empty else []) +
        list(zone_after["dept"].unique()  if not zone_after.empty  else [])
    ))

    before_counts_map = zone_before.groupby("dept").size().to_dict() if not zone_before.empty else {}
    after_counts_map  = zone_after.groupby("dept").size().to_dict()  if not zone_after.empty  else {}

    before_counts = [before_counts_map.get(d, 0) for d in all_depts]
    after_counts  = [after_counts_map.get(d, 0)  for d in all_depts]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Before Images",
        y=all_depts,
        x=before_counts,
        orientation="h",
        marker=dict(color="#1a73e8", opacity=0.88, line=dict(width=0)),
        text=before_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Before Images: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="After Images",
        y=all_depts,
        x=after_counts,
        orientation="h",
        marker=dict(color="#2a9d8f", opacity=0.88, line=dict(width=0)),
        text=after_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>After Images: %{x}<extra></extra>",
    ))

    fig_height = max(400, len(all_depts) * 45 + 100)
    fig.update_layout(
        title=dict(
            text=f"Images per Department — {active_tab} (All Time, Before vs After)",
            font=dict(size=14, color="#333"),
        ),
        xaxis_title="Number of Images",
        yaxis_title="",
        template="plotly_white",
        height=fig_height,
        margin=dict(l=200, r=100, t=50, b=60),  # Increase left margin to 200px for label width, increase bottom margin to 60px for ticks and label
        barmode="group",
        bargap=0.15,
        bargroupgap=0.05,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=all_depts[::-1]  # Display in clean top-to-bottom alphabetical order
        )
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Department bar chart (for selected zone tab - Area Code 0 Only)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-dept-bar-chart-ac0", "figure"),
    Input("k5t-zone-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_dept_bar_ac0(active_tab, _n):
    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=400,
        annotations=[dict(
            text="Select a zone tab above to see department trends (Area Code 0)",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=15, color="#999"),
        )],
    )

    if not active_tab:
        return empty_fig

    before_df = k5t_load_submissions()
    after_df  = k5t_load_after_submissions()

    zone_before = before_df[before_df["zone"] == active_tab] if not before_df.empty else pd.DataFrame()
    zone_after  = after_df[after_df["zone"] == active_tab]   if not after_df.empty  else pd.DataFrame()

    if zone_before.empty and zone_after.empty:
        empty_fig.update_layout(
            annotations=[dict(
                text=f"No images submitted for {active_tab} yet",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=15, color="#999"),
            )]
        )
        return empty_fig

    # 1. Build pending area code map
    pending_map = {}
    for path in [_PENDING_CSV, _GREENERY_CSV]:
        if not os.path.isfile(path):
            continue
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    zone = row.get("zone", "").strip()
                    dept = row.get("dept", "").strip()
                    bf = row.get("before_file", "").strip()
                    af = row.get("after_file", "").strip()
                    ac = row.get("area_code", "").strip()
                    if bf:
                        pending_map[(zone, dept, bf)] = ac
                    if af:
                        pending_map[(zone, dept, af)] = ac
        except Exception:
            pass

    # 2. Build text maps for approved files in the active zone
    from apps.progress import load_text_map as load_prog_text_map
    from apps.greenery import load_text_map as load_green_text_map

    depts = set(
        list(zone_before["dept"].unique() if not zone_before.empty else []) +
        list(zone_after["dept"].unique()  if not zone_after.empty  else [])
    )
    text_maps = {}
    for d in depts:
        p_map = load_prog_text_map(active_tab, d)
        g_map = load_green_text_map(active_tab, d)
        merged = {}
        if p_map:
            merged.update(p_map)
        if g_map:
            merged.update(g_map)
        text_maps[(active_tab, d)] = merged

    # Helper function to check if area code is 0
    def is_area_zero(val):
        if val is None:
            return False
        val_str = str(val).strip()
        if val_str == "0" or val_str == "0.0":
            return True
        try:
            if float(val_str) == 0.0:
                return True
        except ValueError:
            pass
        return False

    def get_area_code(zone, dept, file_name, is_after, status):
        lookup_name = file_name
        if is_after:
            parts = file_name.split('.')
            if len(parts) == 4 and parts[1] == "1":
                lookup_name = f"{parts[0]}.{parts[2]}.{parts[3]}"

        if status == "approved":
            # Check approved text maps first
            map_key = (zone, dept)
            if map_key in text_maps:
                t_map = text_maps[map_key]
                if lookup_name in t_map:
                    ac = t_map[lookup_name].get("area_code", "")
                    if ac:
                        return ac
            # Fallback to pending map
            key = (zone, dept, file_name)
            if key in pending_map:
                return pending_map[key]
        else:
            # Check pending map first
            key = (zone, dept, file_name)
            if key in pending_map:
                ac = pending_map[key]
                if ac:
                    return ac
            # Fallback to approved maps
            map_key = (zone, dept)
            if map_key in text_maps:
                t_map = text_maps[map_key]
                if lookup_name in t_map:
                    return t_map[lookup_name].get("area_code", "")
        return ""

    # Filter zone_before and zone_after by area code == 0
    if not zone_before.empty:
        ac_list = [get_area_code(row["zone"], row["dept"], row["file_name"], False, row["status"]) for _, row in zone_before.iterrows()]
        zone_before = zone_before.copy()
        zone_before["area_code"] = ac_list
        zone_before = zone_before[zone_before["area_code"].apply(is_area_zero)]

    if not zone_after.empty:
        ac_list = [get_area_code(row["zone"], row["dept"], row["file_name"], True, row["status"]) for _, row in zone_after.iterrows()]
        zone_after = zone_after.copy()
        zone_after["area_code"] = ac_list
        zone_after = zone_after[zone_after["area_code"].apply(is_area_zero)]

    # Map department names in submissions to their HOD/canonical grouped labels to completely eliminate duplicates
    mapping = k5t_get_canonical_dept_mapping(active_tab)
    if not zone_before.empty:
        zone_before = zone_before.copy()
        zone_before["dept"] = zone_before["dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )
    if not zone_after.empty:
        zone_after = zone_after.copy()
        zone_after["dept"] = zone_after["dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )

    if zone_before.empty and zone_after.empty:
        empty_fig.update_layout(
            annotations=[dict(
                text=f"No area code 0 images submitted for {active_tab} yet",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=15, color="#999"),
            )]
        )
        return empty_fig

    # Re-calculate deduplicated departments list
    all_depts = sorted(set(
        list(zone_before["dept"].unique() if not zone_before.empty else []) +
        list(zone_after["dept"].unique()  if not zone_after.empty  else [])
    ))

    before_counts_map = zone_before.groupby("dept").size().to_dict() if not zone_before.empty else {}
    after_counts_map  = zone_after.groupby("dept").size().to_dict()  if not zone_after.empty  else {}

    before_counts = [before_counts_map.get(d, 0) for d in all_depts]
    after_counts  = [after_counts_map.get(d, 0)  for d in all_depts]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Before Images",
        y=all_depts,
        x=before_counts,
        orientation="h",
        marker=dict(color="#1a73e8", opacity=0.88, line=dict(width=0)),
        text=before_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Before Images: %{x}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="After Images",
        y=all_depts,
        x=after_counts,
        orientation="h",
        marker=dict(color="#2a9d8f", opacity=0.88, line=dict(width=0)),
        text=after_counts,
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>After Images: %{x}<extra></extra>",
    ))

    fig_height = max(400, len(all_depts) * 45 + 100)
    fig.update_layout(
        title=dict(
            text=f"Images per Department — {active_tab} (All Time, Before vs After - Area Code 0 Only)",
            font=dict(size=14, color="#333"),
        ),
        xaxis_title="Number of Images",
        yaxis_title="",
        template="plotly_white",
        height=fig_height,
        margin=dict(l=200, r=100, t=50, b=60),
        barmode="group",
        bargap=0.15,
        bargroupgap=0.05,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(
            type="category",
            categoryorder="array",
            categoryarray=all_depts[::-1]
        )
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: populate dept dot tabs (All + depts in selected zone)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-ddot-dept-tabs", "children"),
    Output("k5t-ddot-dept-tabs", "active_tab"),
    Input("k5t-zone-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
    State("k5t-ddot-dept-tabs", "active_tab"),
)
def k5t_build_ddot_dept_tabs(zone_tab, _n, current_active):
    """Populate dept tabs with All + each dept in the selected zone."""
    depts = k5t_get_depts_for_zone(zone_tab) if zone_tab else []
    tabs = [dbc.Tab(label="All", tab_id="__all__")] + [
        dbc.Tab(label=d, tab_id=d) for d in depts
    ]
    
    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    
    # If the user manually switched the zone tab, reset the department tab to "All"
    if trigger == "k5t-zone-tabs":
        return tabs, "__all__"
        
    # Otherwise (e.g. periodic refresh), preserve the active selection if it remains valid
    valid_ids = ["__all__"] + depts
    if current_active in valid_ids:
        return tabs, current_active
        
    return tabs, "__all__"


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Department dotted trend (filtered by zone tab + dept tab)
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-dept-dot-chart", "figure"),
    Input("k5t-zone-tabs", "active_tab"),
    Input("k5t-ddot-dept-tabs", "active_tab"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_dept_dot(zone_tab, dept_tab, _n):
    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=440,
        annotations=[dict(
            text="Select a zone tab above to see department dotted trends",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=15, color="#999"),
        )],
    )

    if not zone_tab:
        return empty_fig

    before_df = k5t_load_submissions()
    after_df  = k5t_load_after_submissions()

    # Map department names in submissions to their HOD/canonical grouped labels to completely eliminate duplicates
    mapping = k5t_get_canonical_dept_mapping(zone_tab)
    if not before_df.empty:
        before_df = before_df.copy()
        mask = before_df["zone"] == zone_tab
        before_df.loc[mask, "dept"] = before_df.loc[mask, "dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )
    if not after_df.empty:
        after_df = after_df.copy()
        mask = after_df["zone"] == zone_tab
        after_df.loc[mask, "dept"] = after_df.loc[mask, "dept"].astype(str).str.strip().map(
            lambda x: mapping.get(x, mapping.get(x.casefold(), x))
        )

    cutoff = (datetime.now() - timedelta(days=30)).date()
    grouped_map = k5t_get_grouped_depts_for_zone(zone_tab)
    selected_label = dept_tab if dept_tab and dept_tab != "__all__" else None

    def _filter_dept_df(df):
        if df.empty:
            return df
        d = df[(df["zone"] == zone_tab) & (df["date"] >= cutoff)].copy()
        if selected_label:
            member_depts = grouped_map.get(selected_label, [])
            normalized_allowed = {
                k5t_normalize_dept_name(name)
                for name in [*member_depts, selected_label]
            }
            d = d[d["dept"].map(k5t_normalize_dept_name).isin(normalized_allowed)]
        return d

    before30 = _filter_dept_df(before_df)
    after30  = _filter_dept_df(after_df)

    if before30.empty and after30.empty:
        empty_fig.update_layout(
            annotations=[dict(
                text=f"No submissions for {zone_tab} in the past 30 days",
                x=0.5, y=0.5, xref="paper", yref="paper",
                showarrow=False, font=dict(size=15, color="#999"),
            )]
        )
        return empty_fig

    all_depts_global = sorted(set(
        list(before30["dept"].unique() if not before30.empty else []) +
        list(after30["dept"].unique()  if not after30.empty  else [])
    ))
    color_map = {d: COLORS[i % len(COLORS)] for i, d in enumerate(all_depts_global)}

    dept_label = selected_label if selected_label else "All Departments"
    title_text = f"Daily Submissions — {zone_tab} / {dept_label} — Past 30 Days (Solid=Before, Dotted=After)"

    fig = go.Figure()

    # Before traces (solid)
    if not before30.empty:
        daily_b = before30.groupby(["date", "dept"]).size().reset_index(name="count")
        for dept in sorted(daily_b["dept"].unique()):
            grp = daily_b[daily_b["dept"] == dept].sort_values("date")
            date_strs = [str(d) for d in grp["date"]]
            text_labels = [""] * len(grp)
            if len(grp) > 0:
                text_labels[-1] = f" <b>{dept} (B)</b>"
            fig.add_trace(go.Scatter(
                x=date_strs, y=grp["count"],
                mode="lines+markers+text",
                text=text_labels, textposition="top right",
                name=f"{dept} — Before",
                legendgroup=dept,
                marker=dict(color=color_map[dept], size=9, symbol="circle",
                            line=dict(width=1.5, color="white")),
                line=dict(color=color_map[dept], width=2.5, dash="solid"),
                hovertemplate=f"<b>{dept} — Before</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>",
            ))

    # After traces (dotted)
    if not after30.empty:
        daily_a = after30.groupby(["date", "dept"]).size().reset_index(name="count")
        for dept in sorted(daily_a["dept"].unique()):
            grp = daily_a[daily_a["dept"] == dept].sort_values("date")
            date_strs = [str(d) for d in grp["date"]]
            text_labels = [""] * len(grp)
            if len(grp) > 0:
                text_labels[-1] = f" <b>{dept} (A)</b>"
            fig.add_trace(go.Scatter(
                x=date_strs, y=grp["count"],
                mode="lines+markers+text",
                text=text_labels, textposition="top right",
                name=f"{dept} — After",
                legendgroup=dept,
                marker=dict(color=color_map[dept], size=9, symbol="diamond",
                            line=dict(width=1.5, color="white")),
                line=dict(color=color_map[dept], width=2.5, dash="dot"),
                hovertemplate=f"<b>{dept} — After</b><br>Date: %{{x}}<br>Count: %{{y}}<extra></extra>",
            ))

    fig.update_layout(
        title=dict(text=title_text, font=dict(size=14, color="#333")),
        xaxis_title="Date",
        yaxis_title="Number of Images",
        template="plotly_white",
        height=440,
        margin=dict(l=20, r=160, t=50, b=50),
        showlegend=True,
        legend=dict(orientation="v", x=1.01, y=1),
        xaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
        yaxis=dict(showgrid=True, gridcolor="#f0f0f0"),
    )
    return fig


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACK: Status pie/donut chart by zone
# ─────────────────────────────────────────────────────────────────────────────

@_app.callback(
    Output("k5t-status-before-chart", "figure"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_before_status_chart(_n):
    df = k5t_load_submissions()

    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0), height=360,
        annotations=[dict(
            text="No before-image submission data available yet",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=16, color="#999"),
        )],
    )

    if df.empty:
        return empty_fig

    # Keep only the three display statuses; orphaned disk images already carry
    # an inferred status (approved / pending) so no rows are lost here —
    # this purely guards against any unexpected status strings.
    _DISPLAY = ["approved", "pending", "rejected"]
    df = df[df["status"].isin(_DISPLAY)]
    if df.empty:
        return empty_fig

    status_zone = df.groupby(["zone", "status"]).size().reset_index(name="count")
    all_zones = sorted(status_zone["zone"].unique())
    statuses = [s for s in _DISPLAY if s in status_zone["status"].unique()]
    status_colors = {
        "approved": "#2a9d8f",
        "pending":  "#e9c46a",
        "rejected": "#e63946",
    }

    fig = go.Figure()
    for st in statuses:
        st_df = status_zone[status_zone["status"] == st]
        counts = []
        for z in all_zones:
            val = st_df[st_df["zone"] == z]["count"].values
            counts.append(int(val[0]) if len(val) > 0 else 0)
        fig.add_trace(go.Bar(
            name=st.capitalize(),
            x=all_zones,
            y=counts,
            marker_color=status_colors.get(st, "#457b9d"),
            text=counts,
            textposition="outside",
            hovertemplate=f"<b>%{{x}}</b><br>{st.capitalize()}: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="Before Image Status by Zone (Approved / Pending / Rejected)",
                   font=dict(size=14, color="#333")),
        barmode="group",
        xaxis_title="Zone",
        yaxis_title="Count",
        template="plotly_white",
        height=360,
        margin=dict(l=20, r=20, t=50, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.2,
        bargroupgap=0.05,
    )
    return fig


@_app.callback(
    Output("k5t-status-after-chart", "figure"),
    Input("k5t-refresh-interval", "n_intervals"),
)
def k5t_update_after_status_chart(_n):
    df = k5t_load_after_submissions()

    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=0, r=0, t=40, b=0), height=360,
        annotations=[dict(
            text="No after-image submission data available yet",
            x=0.5, y=0.5, xref="paper", yref="paper",
            showarrow=False, font=dict(size=16, color="#999"),
        )],
    )

    if df.empty:
        return empty_fig

    _DISPLAY = ["approved", "pending", "rejected"]
    df = df[df["status"].isin(_DISPLAY)]
    if df.empty:
        return empty_fig

    status_zone = df.groupby(["zone", "status"]).size().reset_index(name="count")
    all_zones = sorted(status_zone["zone"].unique())
    statuses = [s for s in _DISPLAY if s in status_zone["status"].unique()]
    status_colors = {
        "approved": "#1a73e8",
        "pending":  "#f4a261",
        "rejected": "#c9184a",
    }

    fig = go.Figure()
    for st in statuses:
        st_df = status_zone[status_zone["status"] == st]
        counts = []
        for z in all_zones:
            val = st_df[st_df["zone"] == z]["count"].values
            counts.append(int(val[0]) if len(val) > 0 else 0)
        fig.add_trace(go.Bar(
            name=st.capitalize(),
            x=all_zones,
            y=counts,
            marker_color=status_colors.get(st, "#457b9d"),
            text=counts,
            textposition="outside",
            hovertemplate=f"<b>%{{x}}</b><br>{st.capitalize()}: %{{y}}<extra></extra>",
        ))

    fig.update_layout(
        title=dict(text="After Image Status by Zone (Approved / Pending / Rejected)",
                   font=dict(size=14, color="#333")),
        barmode="group",
        xaxis_title="Zone",
        yaxis_title="Count",
        template="plotly_white",
        height=360,
        margin=dict(l=20, r=20, t=50, b=80),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        bargap=0.2,
        bargroupgap=0.05,
    )
    return fig
