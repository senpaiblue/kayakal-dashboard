import dash
import os
import csv
import base64
import pandas as pd
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from datetime import datetime

# Remove register_page as index.py manages it without dash pages.
# dash.register_page(__name__, path="/red-tag-trends")

# ─────────────────────────────────────────────────────────────────────────────
# DATA HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_DEP_CSV = "./assets/k5/dep.csv"
_PENDING_CSV = "./Data/red_tag_pending.csv"
_RED_BASE_PATH = "./assets/K5"

COLORS = [
    "#e63946", "#2a9d8f", "#e9c46a", "#264653",
    "#f4a261", "#457b9d", "#a8dadc", "#6a4c93",
    "#1982c4", "#8ac926", "#ff6b6b", "#48cae4",
]


def rtt_load_dep_csv():
    try:
        return pd.read_csv(_DEP_CSV, encoding="cp1252")
    except Exception:
        return pd.DataFrame(columns=["DIC ZONE NAME", "Department", "HOD"])


def rtt_get_zones():
    df = rtt_load_dep_csv()
    return list(dict.fromkeys(df["DIC ZONE NAME"].dropna()))


def rtt_load_submissions():
    """Load unsold submissions for Red Tag Trends (all statuses)."""
    rows = []
    path = _PENDING_CSV
    if not os.path.isfile(path):
        return pd.DataFrame(columns=[
            "id", "zone", "dept", "item_file", "spec_file",
            "total_items", "total_evaluation", "sorted",
            "status", "submitted_at", "contact_phone", "date",
        ])
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                zone = row.get("zone", "").strip()
                dept = row.get("dept", "").strip()
                submitted = row.get("submitted_at", "").strip()
                status = row.get("status", "").strip()
                ti_str = row.get("total_items", "").strip()
                te_str = row.get("total_evaluation", "").strip()

                ti = float(ti_str) if ti_str else 0.0
                te = float(te_str) if te_str else 0.0
                sorted_flag = (row.get("sorted", "") or "").strip().lower()

                # "sorted" means item is sold, so hide it from trends.
                if sorted_flag in {"yes", "y", "true", "1", "sold"}:
                    continue

                if not zone or not submitted:
                    continue
                try:
                    dt = datetime.strptime(submitted, "%Y-%m-%d %H:%M:%S")
                except Exception:
                    continue

                rows.append({
                    "id": row.get("id", "").strip(),
                    "zone": zone,
                    "dept": dept,
                    "item_file": row.get("item_file", "").strip(),
                    "spec_file": row.get("spec_file", "").strip(),
                    "total_items": ti,
                    "total_evaluation": te,
                    "sorted": row.get("sorted", "").strip(),
                    "status": status,
                    "submitted_at": submitted,
                    "contact_phone": (row.get("contact_phone", "") or "").strip(),
                    "date": dt,
                })
    except Exception:
        pass

    if not rows:
        return pd.DataFrame(columns=[
            "id", "zone", "dept", "item_file", "spec_file",
            "total_items", "total_evaluation", "sorted",
            "status", "submitted_at", "contact_phone", "date",
        ])
    return pd.DataFrame(rows)


def rtt_img_to_uri(path):
    """Encode an image file to a data URI (base64)."""
    try:
        if not path or not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return "data:image/jpeg;base64," + base64.b64encode(f.read()).decode()
    except Exception:
        return None


def rtt_resolve_image_path(zone, dept, filename, status):
    """Approved images live in .../red/, pending in .../red/pending/."""
    if not filename:
        return None
    base = os.path.join(_RED_BASE_PATH, zone, dept, "red")
    if (status or "").lower() == "pending":
        return os.path.join(base, "pending", filename)
    return os.path.join(base, filename)


# ─────────────────────────────────────────────────────────────────────────────
# CARD STYLES
# ─────────────────────────────────────────────────────────────────────────────

CARD_STYLE = {
    "background": "white",
    "borderRadius": "14px",
    "boxShadow": "0 4px 14px rgba(0,0,0,0.08)",
    "overflow": "hidden",
    "display": "flex",
    "flexDirection": "column",
    "transition": "transform 0.2s ease, box-shadow 0.2s ease",
}

BADGE_BASE = {
    "display": "inline-block",
    "padding": "4px 10px",
    "borderRadius": "999px",
    "fontSize": "11px",
    "fontWeight": "700",
    "letterSpacing": "0.3px",
    "textTransform": "uppercase",
}


def _status_badge(status):
    s = (status or "").lower()
    if s == "approved":
        color = "#2a9d8f"
        bg = "#e6f7f4"
    elif s == "pending":
        color = "#b07500"
        bg = "#fff6dc"
    elif s == "rejected":
        color = "#c0392b"
        bg = "#fdecea"
    else:
        color = "#555"
        bg = "#eee"
    st = {**BADGE_BASE, "color": color, "background": bg}
    return html.Span(status.title() if status else "—", style=st)


def _chip(label, value, bg="#f1f3f9", fg="#333"):
    return html.Span([
        html.Span(label, style={"fontSize": "10px", "color": "#777",
                                 "fontWeight": "600", "marginRight": "4px",
                                 "textTransform": "uppercase"}),
        html.Span(value, style={"fontSize": "12px", "fontWeight": "700", "color": fg}),
    ], style={
        "display": "inline-flex",
        "alignItems": "center",
        "padding": "4px 10px",
        "borderRadius": "8px",
        "background": bg,
        "marginRight": "6px",
        "marginBottom": "4px",
    })


def rtt_build_product_card(row):
    zone = row.get("zone", "")
    dept = row.get("dept", "")
    status = row.get("status", "")
    submitted_at = row.get("submitted_at", "")
    total_items = row.get("total_items", 0) or 0
    total_eval = row.get("total_evaluation", 0) or 0
    sorted_flag = (row.get("sorted", "") or "").lower()
    contact_phone = str(row.get("contact_phone", "") or "").strip()

    item_path = rtt_resolve_image_path(zone, dept, row.get("item_file", ""), status)
    spec_path = rtt_resolve_image_path(zone, dept, row.get("spec_file", ""), status)

    item_uri = rtt_img_to_uri(item_path)
    spec_uri = rtt_img_to_uri(spec_path)

    # Image area (two stacked thumbnails if available)
    if item_uri or spec_uri:
        img_children = []
        if item_uri:
            img_children.append(html.Img(
                src=item_uri,
                style={
                    "width": "100%", "height": "180px",
                    "objectFit": "cover", "display": "block",
                },
            ))
        if spec_uri:
            img_children.append(html.Img(
                src=spec_uri,
                style={
                    "width": "100%", "height": "100px",
                    "objectFit": "cover", "display": "block",
                    "borderTop": "2px solid #fff",
                    "opacity": "0.95",
                },
            ))
        image_block = html.Div(img_children, style={
            "background": "#111",
            "display": "flex",
            "flexDirection": "column",
        })
    else:
        image_block = html.Div("No Image Available", style={
            "height": "180px",
            "background": "linear-gradient(135deg,#fde2e4,#f8d7da)",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "color": "#9e2a2b",
            "fontWeight": "600",
            "fontSize": "13px",
        })

    zone_badge = html.Span(zone or "—", style={
        **BADGE_BASE, "color": "#1d3557", "background": "#e3f0ff",
    })
    dept_badge = html.Span(dept or "—", style={
        **BADGE_BASE, "color": "#6a4c93", "background": "#efe7fb",
    })

    sorted_badge = None
    if sorted_flag == "yes":
        sorted_badge = html.Span("✓ Sorted", style={
            **BADGE_BASE, "color": "#2a9d8f", "background": "#e6f7f4",
        })

    if contact_phone:
        contact_block = html.A(
            [
                html.Span("📞", style={"marginRight": "8px", "fontSize": "16px"}),
                html.Div([
                    html.Div("Contact to Buy", style={
                        "fontSize": "10px",
                        "fontWeight": "700",
                        "color": "#fff",
                        "opacity": "0.85",
                        "textTransform": "uppercase",
                        "letterSpacing": "0.4px",
                    }),
                    html.Div(contact_phone, style={
                        "fontSize": "14px",
                        "fontWeight": "700",
                        "color": "#fff",
                        "lineHeight": "1.1",
                    }),
                ]),
            ],
            href=f"tel:{contact_phone}",
            style={
                "display": "flex",
                "alignItems": "center",
                "gap": "4px",
                "background": "linear-gradient(135deg,#e63946,#900c3f)",
                "padding": "8px 12px",
                "borderRadius": "8px",
                "textDecoration": "none",
                "marginBottom": "10px",
                "boxShadow": "0 2px 6px rgba(230,57,70,0.25)",
            },
        )
    else:
        contact_block = html.Div([
            html.Span("📞", style={"marginRight": "6px", "opacity": "0.6"}),
            html.Span("No contact provided", style={
                "fontSize": "12px", "color": "#888", "fontStyle": "italic",
            }),
        ], style={
            "display": "flex", "alignItems": "center",
            "background": "#f5f5f7", "padding": "8px 12px",
            "borderRadius": "8px", "marginBottom": "10px",
        })

    body = html.Div([
        html.Div([
            zone_badge,
            html.Span(" ", style={"display": "inline-block", "width": "6px"}),
            dept_badge,
        ], style={"marginBottom": "10px", "display": "flex", "flexWrap": "wrap", "gap": "6px"}),

        contact_block,

        html.Div([
            _chip("Items", f"{int(total_items)}"),
            _chip("Eval", f"₹ {total_eval:,.0f}", bg="#e6f7f4", fg="#0d6b5e"),
        ], style={"marginBottom": "8px"}),

        html.Div([
            _status_badge(status),
            sorted_badge if sorted_badge else html.Span(),
        ], style={"display": "flex", "gap": "6px", "alignItems": "center",
                  "flexWrap": "wrap", "marginBottom": "8px"}),

        html.Div([
            html.I(className="bi bi-clock", style={"marginRight": "6px", "color": "#888"}),
            html.Span(submitted_at, style={"fontSize": "11px", "color": "#666"}),
        ]),
    ], style={"padding": "14px 16px"})

    return html.Div([image_block, body], style=CARD_STYLE, className="rtt-product-card")


# ─────────────────────────────────────────────────────────────────────────────
# LAYOUT
# ─────────────────────────────────────────────────────────────────────────────

layout = html.Div([
    dcc.Interval(id="rtt-refresh-interval", interval=30_000, n_intervals=0),

    html.Div([
        html.Div([
            html.H2("🟥 Red Tag Trends",
                    style={"margin": "0", "fontWeight": "700",
                           "background": "linear-gradient(90deg,#e63946,#900c3f)",
                           "-webkit-background-clip": "text",
                           "-webkit-text-fill-color": "transparent"}),
            html.P("All listed red tag products across every zone & department",
                   style={"margin": "4px 0 0", "color": "#666", "fontSize": "14px"}),
        ]),
        html.Div([
            dcc.Link(
                html.Button(
                    "←  Back to K5 Trends",
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
                    id="rtt-goto-upload-btn",
                ),
                href="/k5-trends",
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
        html.Div(id="rtt-kpi-row", style={"marginBottom": "28px"}),

        # ── Filter bar ────────────────────────────────────────────
        html.Div([
            html.Div([
                html.Label("Zone", style={"fontSize": "11px", "fontWeight": "700",
                                          "color": "#555", "textTransform": "uppercase"}),
                dcc.Dropdown(
                    id="rtt-gallery-zone-filter",
                    placeholder="All zones",
                    multi=False,
                    clearable=True,
                    style={"minWidth": "200px"},
                ),
            ], style={"flex": "1", "minWidth": "200px"}),

            html.Div([
                html.Label("Department", style={"fontSize": "11px", "fontWeight": "700",
                                                 "color": "#555", "textTransform": "uppercase"}),
                dcc.Dropdown(
                    id="rtt-gallery-dept-filter",
                    placeholder="All departments",
                    multi=False,
                    clearable=True,
                    style={"minWidth": "200px"},
                ),
            ], style={"flex": "1", "minWidth": "200px"}),

            html.Div([
                html.Label("Status", style={"fontSize": "11px", "fontWeight": "700",
                                             "color": "#555", "textTransform": "uppercase"}),
                dcc.Dropdown(
                    id="rtt-gallery-status-filter",
                    options=[
                        {"label": "All", "value": "__all__"},
                        {"label": "Approved", "value": "approved"},
                        {"label": "Pending", "value": "pending"},
                        {"label": "Rejected", "value": "rejected"},
                    ],
                    value="__all__",
                    clearable=False,
                    style={"minWidth": "160px"},
                ),
            ], style={"flex": "0.6", "minWidth": "160px"}),

            html.Div([
                html.Label("Search", style={"fontSize": "11px", "fontWeight": "700",
                                             "color": "#555", "textTransform": "uppercase"}),
                dcc.Input(
                    id="rtt-gallery-search",
                    placeholder="Search zone, dept, id or phone…",
                    type="text",
                    debounce=True,
                    style={
                        "width": "100%",
                        "padding": "7px 12px",
                        "border": "1px solid #d0d5dd",
                        "borderRadius": "6px",
                        "fontSize": "13px",
                    },
                ),
            ], style={"flex": "1.2", "minWidth": "220px"}),
        ], style={
            "display": "flex",
            "gap": "14px",
            "flexWrap": "wrap",
            "alignItems": "flex-end",
            "background": "white",
            "padding": "16px 20px",
            "borderRadius": "14px",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.06)",
            "marginBottom": "18px",
        }),

        # ── Product gallery ──────────────────────────────────────
        html.Div([
            html.Div([
                html.H4("🏷️ All Red Tag Products",
                        style={"fontWeight": "700", "margin": "0", "color": "#1a1a2e"}),
                html.Span(id="rtt-gallery-count", style={
                    "marginLeft": "12px",
                    "fontSize": "13px",
                    "fontWeight": "600",
                    "color": "#e63946",
                    "background": "#fde2e4",
                    "padding": "3px 10px",
                    "borderRadius": "999px",
                }),
            ], style={"display": "flex", "alignItems": "center", "marginBottom": "16px"}),

            html.Div(id="rtt-gallery-grid", style={
                "display": "grid",
                "gridTemplateColumns": "repeat(auto-fill, minmax(260px, 1fr))",
                "gap": "18px",
            }),
        ], style={
            "background": "white", "borderRadius": "14px", "padding": "24px",
            "boxShadow": "0 2px 16px rgba(0,0,0,0.07)", "marginBottom": "24px",
        }),

    ], style={"padding": "28px", "maxWidth": "1400px", "margin": "0 auto"}),

], style={"background": "#f4f7fc", "minHeight": "100vh", "fontFamily": "Inter, sans-serif"})


# ─────────────────────────────────────────────────────────────────────────────
# CALLBACKS
# ─────────────────────────────────────────────────────────────────────────────

@dash.callback(
    Output("rtt-kpi-row", "children"),
    Input("rtt-refresh-interval", "n_intervals"),
)
def rtt_update_kpis(_n):
    df = rtt_load_submissions()

    total_tags = len(df)
    pending_tags = len(df[df["status"] == "pending"]) if not df.empty else 0
    total_eval = df["total_evaluation"].sum() if not df.empty else 0

    today = datetime.now().date()
    today_count = len(df[df["date"].dt.date == today]) if not df.empty else 0

    def kpi_card(value, label, color, icon, style_override=None):
        base_style = {
            "background": "white",
            "borderRadius": "14px",
            "padding": "20px 24px",
            "boxShadow": "0 2px 12px rgba(0,0,0,0.07)",
            "flex": "1",
            "minWidth": "160px",
            "textAlign": "center",
            "borderTop": f"4px solid {color}",
        }
        if style_override:
            base_style.update(style_override)

        val_str = str(value)
        font_size = "32px"
        if len(val_str) > 10:
            font_size = "26px"
        elif len(val_str) > 14:
            font_size = "22px"

        return html.Div([
            html.Div(icon, style={"fontSize": "28px", "marginBottom": "6px"}),
            html.Div(val_str, style={
                "fontSize": font_size, "fontWeight": "800", "color": color,
                "lineHeight": "1", "wordBreak": "break-word"
            }),
            html.Div(label, style={
                "fontSize": "13px", "color": "#666", "marginTop": "4px", "fontWeight": "500"
            }),
        ], style=base_style)

    return html.Div([
        kpi_card(total_tags, "Total Red Tags Submitted", "#e63946", "🟥"),
        kpi_card(pending_tags, "Pending Approvals", "#e9c46a", "⏳"),
        kpi_card(
            f"₹ {total_eval:,.2f}",
            "Total Evaluation Value",
            "#2a9d8f",
            "💰",
            style_override={"flex": "1.5", "minWidth": "250px"}
        ),
        kpi_card(today_count, "Submitted Today", "#6a4c93", "🕐"),
    ], style={"display": "flex", "gap": "16px", "flexWrap": "wrap"})


@dash.callback(
    Output("rtt-gallery-zone-filter", "options"),
    Input("rtt-refresh-interval", "n_intervals"),
)
def rtt_populate_zone_filter(_n):
    df = rtt_load_submissions()
    zones = sorted(df["zone"].dropna().unique().tolist()) if not df.empty else []
    return [{"label": z, "value": z} for z in zones]


@dash.callback(
    Output("rtt-gallery-dept-filter", "options"),
    Input("rtt-gallery-zone-filter", "value"),
    Input("rtt-refresh-interval", "n_intervals"),
)
def rtt_populate_dept_filter(zone_val, _n):
    df = rtt_load_submissions()
    if df.empty:
        return []
    if zone_val:
        df = df[df["zone"] == zone_val]
    depts = sorted(df["dept"].dropna().unique().tolist())
    return [{"label": d, "value": d} for d in depts]


@dash.callback(
    Output("rtt-gallery-grid", "children"),
    Output("rtt-gallery-count", "children"),
    Input("rtt-gallery-zone-filter", "value"),
    Input("rtt-gallery-dept-filter", "value"),
    Input("rtt-gallery-status-filter", "value"),
    Input("rtt-gallery-search", "value"),
    Input("rtt-refresh-interval", "n_intervals"),
)
def rtt_render_gallery(zone_val, dept_val, status_val, search_val, _n):
    df = rtt_load_submissions()

    empty_state = html.Div([
        html.Div("📭", style={"fontSize": "48px", "marginBottom": "10px"}),
        html.Div("No red tag products match your filters",
                 style={"color": "#888", "fontWeight": "600"}),
    ], style={
        "gridColumn": "1 / -1",
        "textAlign": "center",
        "padding": "60px 20px",
    })

    if df.empty:
        return [empty_state], "0 products"

    if zone_val:
        df = df[df["zone"] == zone_val]
    if dept_val:
        df = df[df["dept"] == dept_val]
    if status_val and status_val != "__all__":
        df = df[df["status"] == status_val]

    if search_val:
        q = search_val.strip().lower()
        if q:
            mask = (
                df["zone"].astype(str).str.lower().str.contains(q, na=False)
                | df["dept"].astype(str).str.lower().str.contains(q, na=False)
                | df["id"].astype(str).str.lower().str.contains(q, na=False)
                | df["contact_phone"].astype(str).str.lower().str.contains(q, na=False)
            )
            df = df[mask]

    if df.empty:
        return [empty_state], "0 products"

    df = df.sort_values("date", ascending=False)

    cards = [rtt_build_product_card(row) for _, row in df.iterrows()]
    count_txt = f"{len(df)} product{'s' if len(df) != 1 else ''}"
    return cards, count_txt
