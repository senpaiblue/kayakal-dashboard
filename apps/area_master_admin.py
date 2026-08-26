"""
Area Master Admin — manage 100 area-code rows per zone / department
===================================================================
All Dash component IDs are prefixed with "amgr-" to avoid collisions.
Uses @dash.callback (framework-level) so it works with index.py's app instance.
"""

import os
import csv
import pandas as pd

import dash
from dash import html, dcc, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc

# ── paths ──────────────────────────────────────────────
AREA_MASTER_CSV = os.path.join("Data", "area_master.csv")
AREA_MASTER_COLUMNS = [
    "zone", "dept", "area_code",
    "location_name", "sub_location_name", "responsible_person",
]

# ── helpers ────────────────────────────────────────────

def _ensure_csv():
    if not os.path.isfile(AREA_MASTER_CSV) or os.path.getsize(AREA_MASTER_CSV) == 0:
        with open(AREA_MASTER_CSV, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=AREA_MASTER_COLUMNS).writeheader()


def read_area_master():
    """Return all rows as list of dicts."""
    _ensure_csv()
    with open(AREA_MASTER_CSV, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def read_area_master_for(zone, dept):
    """Return rows filtered to a specific zone + dept, keyed by area_code."""
    data = {}
    for r in read_area_master():
        if r.get("zone") == zone and r.get("dept") == dept:
            try:
                data[int(r["area_code"])] = r
            except (ValueError, KeyError):
                pass
    return data


def update_area_master_single_row(zone, dept, area_code, loc, subloc, person):
    """Update or append a single area code row for a zone & dept."""
    try:
        ac = int(area_code)
    except (ValueError, TypeError):
        return

    all_rows = read_area_master()
    
    # Check if a row already exists for this zone, dept, and area_code
    found = False
    for r in all_rows:
        if r.get("zone") == zone and r.get("dept") == dept and str(r.get("area_code")) == str(ac):
            r["location_name"] = loc
            r["sub_location_name"] = subloc
            r["responsible_person"] = person
            found = True
            break
            
    if not found:
        # Append a new row
        all_rows.append({
            "zone": zone,
            "dept": dept,
            "area_code": str(ac),
            "location_name": loc,
            "sub_location_name": subloc,
            "responsible_person": person,
        })
        
    write_area_master(all_rows)


def write_area_master(rows):
    with open(AREA_MASTER_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=AREA_MASTER_COLUMNS)
        w.writeheader()
        w.writerows(rows)

def get_exec_team_person(zone, dept):
    try:
        et_path = os.path.join("Data", "execution_team.csv")
        dep_path = os.path.join("Data", "Dep vs Score.csv")
        et_local = pd.read_csv(et_path, keep_default_na=False)
        match = et_local[et_local["Area"].str.strip() == dept]
        if not match.empty:
            return str(match.iloc[0]["Execution Team"]).strip()
        
        dep_df = pd.read_csv(dep_path, keep_default_na=False)
        row = dep_df[
            (dep_df["DIC ZONE NAME"] == zone) &
            (dep_df["Department"] == dept)
        ]
        if not row.empty:
            hod_name = str(row.iloc[0]["HOD"]).strip()
            return hod_name
    except Exception:
        pass
    return ""


# ── layout ─────────────────────────────────────────────

layout = dbc.Container([
    html.H4("Area Master — Manage Area Code Data", className="mt-3 mb-2"),
    html.P(
        "Fill in Location Name, Sub Location Name, and Responsible Person "
        "for each area code (1–100). This data auto-populates when uploading images.",
        className="text-muted mb-3",
    ),
    dcc.Link(
        dbc.Button("← Back to Approvals", color="secondary", size="sm"),
        href="/progress-admin",
    ),
    html.Hr(),
    html.Div(id="amgr-table-container"),
    html.Div(id="amgr-save-result", className="mt-3"),
], fluid=True)


# ── Render table ───────────────────────────────────────

@dash.callback(
    Output("amgr-table-container", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def amgr_render_table(zone, dept):
    if not zone or not dept:
        return dbc.Alert(
            "Select a TEC Zone and Department first (go to Kayakalp 5s page).",
            color="warning",
        )

    existing = read_area_master_for(zone, dept)
    exec_person = get_exec_team_person(zone, dept)
    
    # Preload stats by area_code (before/after × pending/approved)
    stats_by_ac = {}
    for p in ["Data/pending_approvals.csv", "Data/greenery_pending.csv"]:
        if os.path.exists(p):
            with open(p, newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("zone") == zone and row.get("dept") == dept:
                        ac_key = row.get("area_code", "").strip()
                        if ac_key:
                            if ac_key not in stats_by_ac:
                                stats_by_ac[ac_key] = {
                                    "before_pending": 0, "before_approved": 0,
                                    "after_pending": 0, "after_approved": 0,
                                }
                            st = row.get("status", "")
                            has_before = bool(row.get("before_file", "").strip())
                            has_after = bool(row.get("after_file", "").strip())
                            is_simultaneous = bool(row.get("location_name", "").strip())
                            if st == "pending":
                                if has_before and (is_simultaneous or not has_after):
                                    stats_by_ac[ac_key]["before_pending"] += 1
                                if has_after:
                                    stats_by_ac[ac_key]["after_pending"] += 1
                            elif st == "approved":
                                if has_before and (is_simultaneous or not has_after):
                                    stats_by_ac[ac_key]["before_approved"] += 1
                                if has_after:
                                    stats_by_ac[ac_key]["after_approved"] += 1

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
            dbc.Col(html.B("Action"), width=1),
        ],
        className="py-2 bg-light border-bottom text-center flex-nowrap",
        style={"position": "sticky", "top": "0", "zIndex": "1", "minWidth": "1400px"}
    )

    rows = [header]
    for ac in range(0, 111):
        rec = existing.get(ac, {})
        def_loc = rec.get("location_name", "")
        def_sub = rec.get("sub_location_name", "")
        def_per = rec.get("responsible_person", "")
        
        if ac == 0 and not def_loc and not def_sub and not def_per:
            def_loc = dept
            def_sub = dept
            def_per = exec_person
            
        ac_stats = stats_by_ac.get(str(ac), {})
        bp = ac_stats.get("before_pending", 0)
        ba = ac_stats.get("before_approved", 0)
        ap = ac_stats.get("after_pending", 0)
        aa = ac_stats.get("after_approved", 0)
            
        rows.append(
            dbc.Row(
                [
                    dbc.Col(
                        html.Span(str(ac), className="fw-bold"),
                        width=1,
                        className="pt-2 text-center",
                    ),
                    dbc.Col(
                        dbc.Input(
                            id={"type": "amgr-loc", "ac": ac},
                            value=def_loc,
                            placeholder="Location Name",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Input(
                            id={"type": "amgr-subloc", "ac": ac},
                            value=def_sub,
                            placeholder="Sub Location Name",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        dbc.Input(
                            id={"type": "amgr-person", "ac": ac},
                            value=def_per,
                            placeholder="Responsible Person",
                            size="sm",
                        ),
                        width=2,
                    ),
                    dbc.Col(
                        html.Span(str(bp), className="text-danger fw-bold"),
                        width=1,
                        className="text-center pt-2"
                    ),
                    dbc.Col(
                        html.Span(str(ba), className="text-success fw-bold"),
                        width=1,
                        className="text-center pt-2"
                    ),
                    dbc.Col(
                        html.Span(str(ap), className="text-danger fw-bold"),
                        width=1,
                        className="text-center pt-2"
                    ),
                    dbc.Col(
                        html.Span(str(aa), className="text-success fw-bold"),
                        width=1,
                        className="text-center pt-2"
                    ),
                    dbc.Col(
                        dbc.Button(
                            "Clear",
                            id={"type": "amgr-del-btn", "ac": ac},
                            color="outline-danger",
                            size="sm",
                            n_clicks=0,
                        ),
                        width=1,
                    ),
                ],
                className="py-1 border-bottom align-items-center flex-nowrap",
                style={"minWidth": "1400px"}
            )
        )

    table_div = html.Div(
        rows,
        style={
            "overflowX": "auto",
            "border": "1px solid #ddd",
            "borderRadius": "5px"
        }
    )

    return [
        table_div,
        dbc.Button(
            "Save All",
            id="amgr-save-all-btn",
            color="success",
            className="mt-3",
        )
    ]


# ── Save All ───────────────────────────────────────────

@dash.callback(
    Output("amgr-save-result", "children"),
    Input("amgr-save-all-btn", "n_clicks"),
    Input({"type": "amgr-del-btn", "ac": ALL}, "n_clicks"),
    State({"type": "amgr-loc", "ac": ALL}, "value"),
    State({"type": "amgr-subloc", "ac": ALL}, "value"),
    State({"type": "amgr-person", "ac": ALL}, "value"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def amgr_save_or_delete(save_n, del_clicks, locs, sublocs, persons, zone, dept):
    if not zone or not dept:
        return dbc.Alert("Zone/Department not selected", color="warning")

    triggered = ctx.triggered_id

    # ── Read all existing rows ──
    all_rows = read_area_master()

    # Remove existing rows for this zone+dept (we'll re-write them)
    other_rows = [
        r for r in all_rows
        if not (r.get("zone") == zone and r.get("dept") == dept)
    ]

    # ── Handle Delete (clear one row) ──
    if isinstance(triggered, dict) and triggered.get("type") == "amgr-del-btn":
        clear_ac = triggered["ac"]
        # Re-add all 111 rows except the cleared one
        for ac in range(0, 111):
            idx = ac
            loc = (locs[idx] or "").strip() if idx < len(locs) else ""
            subloc = (sublocs[idx] or "").strip() if idx < len(sublocs) else ""
            person = (persons[idx] or "").strip() if idx < len(persons) else ""
            if ac == clear_ac:
                loc, subloc, person = "", "", ""
            if loc or subloc or person:
                other_rows.append({
                    "zone": zone,
                    "dept": dept,
                    "area_code": str(ac),
                    "location_name": loc,
                    "sub_location_name": subloc,
                    "responsible_person": person,
                })
        write_area_master(other_rows)
        return dbc.Alert(
            f"Area Code {clear_ac} cleared ✔",
            color="info",
            duration=3000,
        )

    # ── Handle Save All ──
    saved = 0
    for ac in range(0, 111):
        idx = ac
        loc = (locs[idx] or "").strip() if idx < len(locs) else ""
        subloc = (sublocs[idx] or "").strip() if idx < len(sublocs) else ""
        person = (persons[idx] or "").strip() if idx < len(persons) else ""
        if loc or subloc or person:
            other_rows.append({
                "zone": zone,
                "dept": dept,
                "area_code": str(ac),
                "location_name": loc,
                "sub_location_name": subloc,
                "responsible_person": person,
            })
            saved += 1

    write_area_master(other_rows)
    return dbc.Alert(
        f"{saved} area code(s) saved ✔",
        color="success",
        duration=3000,
    )
