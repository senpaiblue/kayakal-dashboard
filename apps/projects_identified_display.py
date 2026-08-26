"""
Projects Identified — Read-only display page.

Shows all project KPI entries for the selected zone / department.
Uses the same CSV store as the admin page:
    assets/K5/{zone}/{dept}/projects_identified.csv
"""

import os
import csv
import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
import urllib.parse

from app import app

BASE_PATH = "./assets/K5"


def _csv_path(zone, dept):
    from apps.progress import get_progress_folder
    folder = os.path.dirname(get_progress_folder(zone, dept))
    return os.path.join(folder, "projects_identified.csv")


_projid_cache = {}

def _read_projid(zone, dept):
    path = _csv_path(zone, dept)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return []
    try:
        mtime = os.path.getmtime(path)
        if path in _projid_cache and _projid_cache[path]["mtime"] == mtime:
            return [row.copy() for row in _projid_cache[path]["data"]]
        with open(path, newline="", encoding="utf-8") as f:
            data = list(csv.DictReader(f))
            _projid_cache[path] = {
                "data": [row.copy() for row in data],
                "mtime": mtime
            }
            return [row.copy() for row in data]
    except Exception:
        with open(path, newline="", encoding="utf-8") as f:
            return list(csv.DictReader(f))


layout = dbc.Container([
    html.H4("Projects Identified", className="mt-3 mb-3 text-primary"),
    dcc.Link(
        dbc.Button("← Back to Department", color="secondary", size="sm"),
        href="/k5",
    ),
    html.Hr(),
    html.Div(id="projid-display-table"),
], fluid=True)


@dash.callback(
    Output("projid-display-table", "children"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def projid_display_render(zone, dept):
    if not zone or not dept:
        return dbc.Alert("Please select a zone and department from the main page.", color="warning")

    rows = _read_projid(zone, dept)
    if not rows:
        return dbc.Alert("No projects identified yet for this department.", color="info")

    header = html.Thead(
        html.Tr([
            html.Th("#", style={"width": "5%"}),
            html.Th("Project Name", style={"width": "25%"}),
            html.Th("KPI Name", style={"width": "25%"}),
            html.Th("KPI From", style={"width": "13%"}),
            html.Th("KPI To", style={"width": "13%"}),
            html.Th("File", style={"width": "19%"}),
        ]),
        className="table-dark"
    )

    body_rows = []
    for i, r in enumerate(rows):
        file_name = r.get("file_name", "")
        if file_name:
            file_url = f"/assets/K5/{urllib.parse.quote(zone)}/{urllib.parse.quote(dept)}/projects_identified_files/{urllib.parse.quote(file_name)}"
            file_cell = html.A(
                f"📎 {file_name}",
                href=file_url,
                target="_blank",
                style={"fontSize": "13px", "wordBreak": "break-all"}
            )
        else:
            file_cell = html.Span("—", style={"color": "#aaa"})

        body_rows.append(html.Tr([
            html.Td(str(i + 1)),
            html.Td(r.get("project_name", "")),
            html.Td(r.get("kpi_name", "")),
            html.Td(r.get("kpi_from", "")),
            html.Td(r.get("kpi_to", "")),
            html.Td(file_cell),
        ]))

    return dbc.Table(
        [header, html.Tbody(body_rows)],
        bordered=True, hover=True, striped=True, responsive=True,
    )
