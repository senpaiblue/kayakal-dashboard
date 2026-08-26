import os
import csv
import uuid
import re
import base64
import time
import dash
from dash import html, dcc, Input, Output, State, ctx, ALL
import dash_bootstrap_components as dbc
import urllib.parse

from app import app

BASE_PATH = "./assets/K5"
PROJID_COLUMNS = ["id", "project_name", "kpi_name", "kpi_from", "kpi_to", "file_name"]


def _csv_path(zone, dept):
    return os.path.join(BASE_PATH, zone, dept, "projects_identified.csv")


def _files_dir(zone, dept):
    return os.path.join(BASE_PATH, zone, dept, "projects_identified_files")


def _sanitize_filename(original_name):
    """Keep original extension, make the base name filesystem-safe.
    Replaces all non-alphanumeric/dot/dash/underscore/space chars with '_'.
    Handles any special characters in the filename.
    """
    if not original_name:
        return ""
    # Split into name and extension
    if "." in original_name:
        base, ext = original_name.rsplit(".", 1)
        ext = "." + ext
    else:
        base = original_name
        ext = ""
    # Replace anything that's NOT alphanumeric, dash, underscore, dot, or space
    safe_base = re.sub(r'[^\w\s\-.]', '_', base, flags=re.UNICODE)
    # Collapse multiple underscores
    safe_base = re.sub(r'_+', '_', safe_base).strip('_').strip()
    if not safe_base:
        safe_base = "file"
    return safe_base + ext


def _read_projid(zone, dept):
    path = _csv_path(zone, dept)
    if not os.path.isfile(path) or os.path.getsize(path) == 0:
        return []
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _write_projid(zone, dept, rows):
    path = _csv_path(zone, dept)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=PROJID_COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            for col in PROJID_COLUMNS:
                r.setdefault(col, "")
            w.writerow(r)


def _save_file(zone, dept, row_id, contents, filename):
    """Save an uploaded file and return the stored filename."""
    if not contents or not filename:
        return ""
    files_folder = _files_dir(zone, dept)
    os.makedirs(files_folder, exist_ok=True)

    safe_name = _sanitize_filename(filename)
    # Prefix with the row_id to avoid collisions
    stored_name = f"{row_id}_{safe_name}"
    try:
        _, encoded = contents.split(",", 1)
        binary = base64.b64decode(encoded)
        file_path = os.path.join(files_folder, stored_name)
        with open(file_path, "wb") as f:
            f.write(binary)
        return stored_name
    except Exception as e:
        print(f"projid file save error: {e}")
        return ""


def _delete_file(zone, dept, file_name):
    """Delete a stored file if it exists."""
    if not file_name:
        return
    file_path = os.path.join(_files_dir(zone, dept), file_name)
    if os.path.isfile(file_path):
        os.remove(file_path)


# ──────────────────────────────────────────────────────────────
# LAYOUT
# ──────────────────────────────────────────────────────────────

layout = dbc.Container([
    html.H4("Projects Identified — Upload", className="mt-3 mb-3 text-primary"),
    html.Div([
        dcc.Link(
            dbc.Button("← Progress Approvals", color="primary", size="sm"),
            href="/progress-admin",
        ),
        dcc.Link(
            dbc.Button("Red Tag Approvals →", color="danger", size="sm", className="ms-2"),
            href="/red-tag-admin",
        ),
        dcc.Link(
            dbc.Button("Greenery Approvals →", color="success", size="sm", className="ms-2"),
            href="/greenery-admin",
        ),
        dcc.Link(
            dbc.Button("Value Credited Approvals →", color="info", size="sm", className="ms-2 text-white fw-bold"),
            href="/value-credited-admin",
        ),
    ]),
    html.Hr(),

    # ── Add New Form ──────────────────────────────────────────
    html.H5("Add New Project", className="mb-3"),
    dbc.Row([
        dbc.Col([
            dbc.Label("Project Name", className="fw-bold"),
            dbc.Input(id="projid-add-project-name", placeholder="Enter project name", type="text"),
        ], md=3),
        dbc.Col([
            dbc.Label("KPI Name", className="fw-bold"),
            dbc.Input(id="projid-add-kpi-name", placeholder="Enter KPI name", type="text"),
        ], md=3),
        dbc.Col([
            dbc.Label("KPI From", className="fw-bold"),
            dbc.Input(id="projid-add-kpi-from", placeholder="Enter KPI from", type="text"),
        ], md=2),
        dbc.Col([
            dbc.Label("KPI To", className="fw-bold"),
            dbc.Input(id="projid-add-kpi-to", placeholder="Enter KPI to", type="text"),
        ], md=2),
        dbc.Col([
            dbc.Label("Attach File (PPT/PDF/Image)", className="fw-bold"),
            dcc.Upload(
                id="projid-add-file-upload",
                children=html.Div([
                    "Drag & Drop or ",
                    html.A("Browse", style={"color": "#0d6efd", "fontWeight": "bold", "textDecoration": "underline"})
                ]),
                style={
                    "height": "38px",
                    "lineHeight": "38px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "cursor": "pointer",
                    "backgroundColor": "#f8f9fa",
                    "fontSize": "13px",
                },
                multiple=False,
            ),
            html.Div(id="projid-add-file-name-display", style={"fontSize": "12px", "color": "#666", "marginTop": "4px"}),
        ], md=2),
    ], className="mb-3"),
    dbc.Button("➕ Add Project", id="projid-add-btn", color="success", size="sm", className="mb-3"),
    html.Div(id="projid-add-msg", className="mb-3"),

    html.Hr(),

    # ── Data Table ────────────────────────────────────────────
    html.H5("Existing Projects", className="mb-3"),
    dcc.Store(id="projid-refresh-trigger", data=0),
    html.Div(id="projid-table-container"),

    # ── Edit Modal ────────────────────────────────────────────
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Edit Project")),
        dbc.ModalBody([
            dcc.Store(id="projid-edit-id"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Project Name", className="fw-bold"),
                    dbc.Input(id="projid-edit-project-name", type="text"),
                ], md=6),
                dbc.Col([
                    dbc.Label("KPI Name", className="fw-bold"),
                    dbc.Input(id="projid-edit-kpi-name", type="text"),
                ], md=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("KPI From", className="fw-bold"),
                    dbc.Input(id="projid-edit-kpi-from", type="text"),
                ], md=6),
                dbc.Col([
                    dbc.Label("KPI To", className="fw-bold"),
                    dbc.Input(id="projid-edit-kpi-to", type="text"),
                ], md=6),
            ], className="mb-3"),
            dbc.Row([
                dbc.Col([
                    dbc.Label("Replace File (leave empty to keep current)", className="fw-bold"),
                    dcc.Upload(
                        id="projid-edit-file-upload",
                        children=html.Div([
                            "Drag & Drop or ",
                            html.A("Browse", style={"color": "#0d6efd", "fontWeight": "bold", "textDecoration": "underline"})
                        ]),
                        style={
                            "height": "38px",
                            "lineHeight": "38px",
                            "borderWidth": "1px",
                            "borderStyle": "dashed",
                            "borderRadius": "5px",
                            "textAlign": "center",
                            "cursor": "pointer",
                            "backgroundColor": "#f8f9fa",
                            "fontSize": "13px",
                        },
                        multiple=False,
                    ),
                    html.Div(id="projid-edit-current-file", style={"fontSize": "12px", "color": "#666", "marginTop": "4px"}),
                ], md=12),
            ]),
        ]),
        dbc.ModalFooter([
            dbc.Button("Save Changes", id="projid-edit-save-btn", color="primary", size="sm"),
            dbc.Button("Cancel", id="projid-edit-cancel-btn", color="secondary", size="sm", className="ms-2"),
        ]),
    ], id="projid-edit-modal", is_open=False, size="lg"),

    html.Div(id="projid-edit-msg", className="mt-2"),
    html.Div(id="projid-delete-msg", className="mt-2"),

], fluid=True)


# ──────────────────────────────────────────────────────────────
# Show selected filename in the Add form
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-add-file-name-display", "children"),
    Input("projid-add-file-upload", "filename"),
    prevent_initial_call=True,
)
def projid_admin_show_add_filename(filename):
    if filename:
        return html.Span(f"📎 {filename}", style={"color": "#198754"})
    return ""


# ──────────────────────────────────────────────────────────────
# Render table
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-table-container", "children"),
    Input("projid-refresh-trigger", "data"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def projid_admin_render_table(_, zone, dept):
    if not zone or not dept:
        return dbc.Alert("Select a zone and department first.", color="warning")

    rows = _read_projid(zone, dept)
    if not rows:
        return dbc.Alert("No projects added yet.", color="info")

    header = html.Thead(html.Tr([
        html.Th("#", style={"width": "4%"}),
        html.Th("Project Name", style={"width": "20%"}),
        html.Th("KPI Name", style={"width": "20%"}),
        html.Th("KPI From", style={"width": "10%"}),
        html.Th("KPI To", style={"width": "10%"}),
        html.Th("File", style={"width": "20%"}),
        html.Th("Actions", style={"width": "16%"}),
    ]))

    body_rows = []
    for i, r in enumerate(rows):
        uid = r.get("id", "")
        file_name = r.get("file_name", "")

        if file_name:
            file_url = f"/assets/K5/{urllib.parse.quote(zone)}/{urllib.parse.quote(dept)}/projects_identified_files/{urllib.parse.quote(file_name)}"
            file_cell = html.A(
                f"📎 {file_name}",
                href=file_url,
                target="_blank",
                style={"fontSize": "12px", "wordBreak": "break-all"}
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
            html.Td([
                dbc.Button("✏️ Edit", id={"type": "projid-edit-btn", "uid": uid},
                           color="warning", size="sm", className="me-1"),
                dbc.Button("🗑️ Delete", id={"type": "projid-delete-btn", "uid": uid},
                           color="danger", size="sm"),
            ]),
        ]))

    return dbc.Table(
        [header, html.Tbody(body_rows)],
        bordered=True, hover=True, striped=True, responsive=True, size="sm"
    )


# ──────────────────────────────────────────────────────────────
# Add entry
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-add-msg", "children"),
    Output("projid-refresh-trigger", "data", allow_duplicate=True),
    Output("projid-add-project-name", "value"),
    Output("projid-add-kpi-name", "value"),
    Output("projid-add-kpi-from", "value"),
    Output("projid-add-kpi-to", "value"),
    Output("projid-add-file-upload", "contents"),
    Output("projid-add-file-name-display", "children", allow_duplicate=True),
    Input("projid-add-btn", "n_clicks"),
    State("projid-add-project-name", "value"),
    State("projid-add-kpi-name", "value"),
    State("projid-add-kpi-from", "value"),
    State("projid-add-kpi-to", "value"),
    State("projid-add-file-upload", "contents"),
    State("projid-add-file-upload", "filename"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def projid_admin_add_entry(n, project_name, kpi_name, kpi_from, kpi_to,
                           file_contents, file_filename, zone, dept):
    if not n:
        raise dash.exceptions.PreventUpdate

    no_update_8 = (dash.no_update,) * 8

    if not zone or not dept:
        return (dbc.Alert("Zone/department not selected.", color="danger"),) + no_update_8[1:]

    if not project_name or not project_name.strip():
        return (dbc.Alert("Project Name is required.", color="warning"),) + no_update_8[1:]

    row_id = str(uuid.uuid4())[:8]

    # Save file if present
    stored_file = ""
    if file_contents and file_filename:
        stored_file = _save_file(zone, dept, row_id, file_contents, file_filename)

    rows = _read_projid(zone, dept)
    new_row = {
        "id": row_id,
        "project_name": (project_name or "").strip(),
        "kpi_name": (kpi_name or "").strip(),
        "kpi_from": (kpi_from or "").strip(),
        "kpi_to": (kpi_to or "").strip(),
        "file_name": stored_file,
    }
    rows.append(new_row)
    _write_projid(zone, dept, rows)

    return (
        dbc.Alert("Project added successfully ✔", color="success", duration=3000),
        time.time(),
        "",  # clear project name
        "",  # clear kpi name
        "",  # clear kpi from
        "",  # clear kpi to
        None,  # clear upload contents
        "",  # clear filename display
    )


# ──────────────────────────────────────────────────────────────
# Delete entry
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-delete-msg", "children"),
    Output("projid-refresh-trigger", "data", allow_duplicate=True),
    Input({"type": "projid-delete-btn", "uid": ALL}, "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def projid_admin_delete_entry(n_clicks_list, zone, dept):
    if not any(n_clicks_list) or not zone or not dept:
        raise dash.exceptions.PreventUpdate

    uid = ctx.triggered_id["uid"]
    rows = _read_projid(zone, dept)

    # Delete associated file
    for r in rows:
        if r.get("id") == uid:
            _delete_file(zone, dept, r.get("file_name", ""))
            break

    rows = [r for r in rows if r.get("id") != uid]
    _write_projid(zone, dept, rows)

    return dbc.Alert("Project deleted ✘", color="danger", duration=3000), time.time()


# ──────────────────────────────────────────────────────────────
# Open edit modal (populate fields)
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-edit-modal", "is_open"),
    Output("projid-edit-id", "data"),
    Output("projid-edit-project-name", "value"),
    Output("projid-edit-kpi-name", "value"),
    Output("projid-edit-kpi-from", "value"),
    Output("projid-edit-kpi-to", "value"),
    Output("projid-edit-current-file", "children"),
    Input({"type": "projid-edit-btn", "uid": ALL}, "n_clicks"),
    Input("projid-edit-cancel-btn", "n_clicks"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def projid_admin_open_edit_modal(edit_clicks, cancel_clicks, zone, dept):
    triggered = ctx.triggered_id

    # Cancel button
    if triggered == "projid-edit-cancel-btn":
        return False, dash.no_update, "", "", "", "", ""

    # Edit button
    if isinstance(triggered, dict) and triggered.get("type") == "projid-edit-btn":
        if not any(edit_clicks) or not zone or not dept:
            raise dash.exceptions.PreventUpdate

        uid = triggered["uid"]
        rows = _read_projid(zone, dept)
        target = None
        for r in rows:
            if r.get("id") == uid:
                target = r
                break
        if not target:
            raise dash.exceptions.PreventUpdate

        current_file = target.get("file_name", "")
        if current_file:
            file_display = html.Span(f"Current file: 📎 {current_file}", style={"color": "#198754"})
        else:
            file_display = html.Span("No file attached", style={"color": "#aaa"})

        return (
            True,
            uid,
            target.get("project_name", ""),
            target.get("kpi_name", ""),
            target.get("kpi_from", ""),
            target.get("kpi_to", ""),
            file_display,
        )

    raise dash.exceptions.PreventUpdate


# ──────────────────────────────────────────────────────────────
# Save edit
# ──────────────────────────────────────────────────────────────

@dash.callback(
    Output("projid-edit-msg", "children"),
    Output("projid-refresh-trigger", "data", allow_duplicate=True),
    Output("projid-edit-modal", "is_open", allow_duplicate=True),
    Input("projid-edit-save-btn", "n_clicks"),
    State("projid-edit-id", "data"),
    State("projid-edit-project-name", "value"),
    State("projid-edit-kpi-name", "value"),
    State("projid-edit-kpi-from", "value"),
    State("projid-edit-kpi-to", "value"),
    State("projid-edit-file-upload", "contents"),
    State("projid-edit-file-upload", "filename"),
    State("selected-zone", "data"),
    State("selected-department", "data"),
    prevent_initial_call=True,
)
def projid_admin_save_edit(n, uid, project_name, kpi_name, kpi_from, kpi_to,
                           file_contents, file_filename, zone, dept):
    if not n or not uid or not zone or not dept:
        raise dash.exceptions.PreventUpdate

    rows = _read_projid(zone, dept)
    for r in rows:
        if r.get("id") == uid:
            r["project_name"] = (project_name or "").strip()
            r["kpi_name"] = (kpi_name or "").strip()
            r["kpi_from"] = (kpi_from or "").strip()
            r["kpi_to"] = (kpi_to or "").strip()

            # Replace file if a new one was uploaded
            if file_contents and file_filename:
                # Delete old file first
                _delete_file(zone, dept, r.get("file_name", ""))
                # Save new file
                stored = _save_file(zone, dept, uid, file_contents, file_filename)
                r["file_name"] = stored

            break
    _write_projid(zone, dept, rows)

    return (
        dbc.Alert("Project updated ✔", color="success", duration=3000),
        time.time(),
        False,  # close modal
    )
