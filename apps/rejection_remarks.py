import os
import base64
from datetime import datetime, timedelta

import dash
from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc

from apps.progress import (
    read_pending_csv,
    write_pending_csv,
    get_pending_folder as get_progress_pending_folder,
    get_progress_folder,
    IMG_STYLE,
    IMG_FRAME_STYLE,
)
from apps.greenery import (
    read_greenery_pending_csv,
    write_greenery_pending_csv,
    get_pending_folder as get_greenery_pending_folder,
    get_greenery_folder,
)


REMARK_RETENTION_DAYS = 24


def _source_configs():
    return [
        {
            "section": "Progress",
            "read": read_pending_csv,
            "write": write_pending_csv,
            "pending_folder": get_progress_pending_folder,
            "main_folder": get_progress_folder,
        },
        {
            "section": "Greenery",
            "read": read_greenery_pending_csv,
            "write": write_greenery_pending_csv,
            "pending_folder": get_greenery_pending_folder,
            "main_folder": get_greenery_folder,
        },
    ]


def _parse_dt(value):
    value = (value or "").strip()
    for fmt in ("%d-%m-%Y %H:%M:%S", "%d-%m-%Y %I:%M:%S %p"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            pass
    return datetime.min


def _img_to_uri(path):
    if not path or not os.path.isfile(path):
        return ""
    with open(path, "rb") as f:
        return "data:image/jpg;base64," + base64.b64encode(f.read()).decode()


def _pending_image_path(row, filename, get_pending_folder):
    if not filename:
        return ""
    path = os.path.join(get_pending_folder(row.get("zone", ""), row.get("dept", "")), filename)
    return path if os.path.isfile(path) else ""


def _visible_image_path(row, filename, get_pending_folder, get_main_folder):
    if not filename:
        return ""
    pending_path = _pending_image_path(row, filename, get_pending_folder)
    if pending_path:
        return pending_path
    main_path = os.path.join(get_main_folder(row.get("zone", ""), row.get("dept", "")), filename)
    return main_path if os.path.isfile(main_path) else ""


def _cleanup_expired_rejected_rows():
    cutoff = datetime.now() - timedelta(days=REMARK_RETENTION_DAYS)

    for config in _source_configs():
        rows = config["read"]()
        kept_rows = []
        changed = False

        for row in rows:
            remark = (row.get("rejection_remark") or "").strip()
            if row.get("status") != "rejected" or not remark:
                kept_rows.append(row)
                continue

            rejected_dt = _parse_dt(row.get("rejected_at") or row.get("submitted_at"))
            if rejected_dt == datetime.min or rejected_dt > cutoff:
                kept_rows.append(row)
                continue

            for file_col in ("before_file", "after_file"):
                image_path = _pending_image_path(row, row.get(file_col, ""), config["pending_folder"])
                if image_path:
                    try:
                        os.remove(image_path)
                    except OSError:
                        pass
            changed = True

        if changed:
            config["write"](kept_rows)


def _rejected_rows(zone=None, dept=None):
    rows = []

    for config in _source_configs():
        section = config["section"]
        source_rows = config["read"]()
        for row in source_rows:
            remark = (row.get("rejection_remark") or "").strip()
            if row.get("status") != "rejected" or not remark:
                continue
            if zone and row.get("zone") != zone:
                continue
            if dept and row.get("dept") != dept:
                continue

            copied = dict(row)
            copied["section"] = section
            copied["pending_folder"] = config["pending_folder"]
            copied["main_folder"] = config["main_folder"]
            copied["rejection_remark"] = remark
            rows.append(copied)

    return sorted(
        rows,
        key=lambda r: _parse_dt(r.get("rejected_at") or r.get("submitted_at")),
        reverse=True,
    )


def _detail(label, value):
    return html.Div(
        [
            html.Span(f"{label}: ", className="fw-bold"),
            html.Span(value or "-"),
        ],
        className="small mb-1",
    )


def _image_panel(title, image_path):
    image = (
        html.Img(src=_img_to_uri(image_path), style=IMG_STYLE)
        if image_path
        else html.Div("Image not available", style={"color": "#888", "fontSize": "14px"})
    )
    return html.Div(
        [
            html.Small(title, className="fw-bold text-muted"),
            html.Div(image, style=IMG_FRAME_STYLE),
        ]
    )


def _remark_card(row):
    section = row.get("section", "")
    badge_color = "primary" if section == "Progress" else "success"
    before_path = _visible_image_path(
        row,
        row.get("before_file", ""),
        row["pending_folder"],
        row["main_folder"],
    )
    after_path = _visible_image_path(
        row,
        row.get("after_file", ""),
        row["pending_folder"],
        row["main_folder"],
    )

    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(
                    [
                        dbc.Badge(section, color=badge_color, className="me-2"),
                        html.Span(
                            row.get("rejected_at") or row.get("submitted_at", ""),
                            className="text-muted small",
                        ),
                    ],
                    className="mb-2",
                ),
                dbc.Row(
                    [
                        dbc.Col(
                            _image_panel("Before", before_path),
                            md=4,
                        ),
                        dbc.Col(
                            _image_panel("After", after_path) if row.get("after_file") else html.Div(
                                "No after image",
                                style={**IMG_FRAME_STYLE, "color": "#888", "fontSize": "14px"},
                            ),
                            md=4,
                        ),
                        dbc.Col(
                            [
                                _detail("Zone", row.get("zone")),
                                _detail("Dept", row.get("dept")),
                                _detail("Location", row.get("location_name")),
                                _detail("Sub Location", row.get("sub_location_name")),
                                _detail("Responsible Person", row.get("responsible_person")),
                                _detail("Area Code", row.get("area_code")),
                                html.Div("Remark", className="fw-bold small mt-2"),
                                html.Div(row.get("rejection_remark"), className="small"),
                            ],
                            md=4,
                        ),
                    ]
                ),
            ]
        ),
        className="mb-3 shadow-sm",
    )


layout = dbc.Container(
    [
        html.H4("Rejection Remarks", className="mt-3 mb-3"),
        html.Div(id="remarks-selected-context", className="text-muted small mb-3"),
        dcc.Interval(id="remarks-refresh-interval", interval=10_000, n_intervals=0),
        html.Div(id="remarks-list-container"),
    ],
    fluid=True,
)


@dash.callback(
    Output("remarks-selected-context", "children"),
    Output("remarks-list-container", "children"),
    Input("remarks-refresh-interval", "n_intervals"),
    Input("selected-zone", "data"),
    Input("selected-department", "data"),
)
def render_rejection_remarks(_n, zone, dept):
    if not zone or not dept:
        return "", dbc.Alert("Select TEC Zone and Department to view rejection remarks.", color="info")

    _cleanup_expired_rejected_rows()
    rows = _rejected_rows(zone, dept)
    context = f"Showing Progress and Greenery rejection remarks for {zone} > {dept}. Items are kept for {REMARK_RETENTION_DAYS} days."

    if not rows:
        return context, dbc.Alert("No rejection remarks found for this selection.", color="info")

    return context, [_remark_card(row) for row in rows]
