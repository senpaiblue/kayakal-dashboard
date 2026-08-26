"""5S audit scoring view: CSV-driven table with S-tabs, month filter, and charts.

Summary charts use Year + Month: plain CSV columns map to calendar years (Nov/Dec → 2025,
Feb/Mar → 2026). Additional waves use headers like november_2026_1s.
"""

import html as html_stdlib
import os
import re

import pandas as pd
import plotly.graph_objects as go
from dash import html, dcc, callback, Input, Output, ctx
import dash_bootstrap_components as dbc

from server import app

D5S_AUDIT_SCORING_CSV = "./Data/5S.csv"
D5S_TAB_COLUMNS = {
    "1S": ["november_1s", "december_1s", "february_1s", "march_1s"],
    "2S": ["december_2s", "february_2s", "march_2s"],
    "3S": ["february_3s", "march_3s"],
    "4S": ["march_4s"],
    "5S": ["march_5s"],
}
D5S_COL_LABELS = {
    "november_1s": "November · 1S",
    "december_1s": "December · 1S",
    "december_2s": "December · 2S",
    "february_1s": "February · 1S",
    "february_2s": "February · 2S",
    "february_3s": "February · 3S",
    "march_1s": "March · 1S",
    "march_2s": "March · 2S",
    "march_3s": "March · 3S",
    "march_4s": "March · 4S",
    "march_5s": "March · 5S",
}
D5S_COLUMN_MONTH = {
    "november_1s": "november",
    "december_1s": "december",
    "december_2s": "december",
    "february_1s": "february",
    "february_2s": "february",
    "february_3s": "february",
    "march_1s": "march",
    "march_2s": "march",
    "march_3s": "march",
    "march_4s": "march",
    "march_5s": "march",
}
D5SA_MONTH_ORDER = ["november", "december", "february", "march"]

D5SA_MONTH_COL_RE = re.compile(r"^([a-z]+)_(\d)s$")
# e.g. november_2026_1s — additional Nov/Dec (or any month) waves for that calendar year
D5SA_EXPLICIT_YEAR_COL_RE = re.compile(r"^([a-z]+)_(\d{4})_(\d)s$")

# Plain CSV columns {month}_Ns (no year in the header) map to these calendar years.
D5SA_MONTH_DEFAULT_YEAR = {
    "november": 2025,
    "december": 2025,
    "february": 2026,
    "march": 2026,
}

# Preferred order for Summary month dropdown (only pairs that exist in CSV are shown).
D5SA_MONTH_YEAR_SORT_ORDER = [
    ("november", 2025),
    ("december", 2025),
    ("february", 2026),
    ("march", 2026),
    ("november", 2026),
    ("december", 2026),
]


def d5sa_s_level_from_column_name(col):
    m = re.search(r"_(\d)s$", str(col).strip().lower())
    return int(m.group(1)) if m else None


def d5sa_sort_month_year_pairs(pairs):
    """Stable order: Nov/Dec 2025, Feb/Mar 2026, then explicit Nov/Dec 2026+, then any other."""
    out = [p for p in D5SA_MONTH_YEAR_SORT_ORDER if p in pairs]
    for p in sorted(pairs):
        if p not in out:
            out.append(p)
    return out


def d5sa_discover_month_year_pairs_in_df(df):
    """(month, year) pairs present in CSV: plain {month}_Ns use D5SA_MONTH_DEFAULT_YEAR; explicit {month}_{year}_Ns."""
    if df is None or df.empty:
        return []
    found: set[tuple[str, int]] = set()
    for c in df.columns:
        if c in ("sl_no", "model_area", "zone"):
            continue
        cl = str(c).strip().lower()
        em = D5SA_EXPLICIT_YEAR_COL_RE.match(cl)
        if em:
            found.add((em.group(1), int(em.group(2))))
            continue
        em2 = D5SA_MONTH_COL_RE.match(cl)
        if em2:
            mon = em2.group(1)
            yy = D5SA_MONTH_DEFAULT_YEAR.get(mon)
            if yy is not None:
                found.add((mon, yy))
    return d5sa_sort_month_year_pairs(found)


def d5sa_list_score_columns_for_month_year(df, month, year):
    """Score column names for a calendar month + year (plain or explicit-year headers)."""
    if df is None or df.empty:
        return []
    m = str(month).strip().lower()
    y = int(year)
    out = []
    for c in df.columns:
        if c in ("sl_no", "model_area", "zone"):
            continue
        cl = str(c).strip().lower()
        em = D5SA_EXPLICIT_YEAR_COL_RE.match(cl)
        if em:
            if em.group(1) == m and int(em.group(2)) == y:
                out.append(c)
            continue
        em2 = D5SA_MONTH_COL_RE.match(cl)
        if em2 and em2.group(1) == m and D5SA_MONTH_DEFAULT_YEAR.get(m) == y:
            out.append(c)
    return sorted(out, key=lambda col: d5sa_s_level_from_column_name(col) or 0)


def d5sa_split_month_year_value(month_val):
    """Milestone month dropdown value 'march:2026' → ('march', 2026). Legacy 'march' → default year."""
    if not month_val:
        return None, None
    s = str(month_val).strip()
    if ":" in s:
        a, b = s.split(":", 1)
        return a.strip().lower(), int(b)
    m = s.lower()
    return m, D5SA_MONTH_DEFAULT_YEAR.get(m)


def d5sa_milestone_selection_label(month_val):
    m, y = d5sa_split_month_year_value(month_val)
    if m and y is not None:
        return f"{m.capitalize()} {y}"
    return str(month_val) if month_val else ""


def d5sa_human_column_label(col: str) -> str:
    """Readable label for hover for any score column."""
    if col in D5S_COL_LABELS:
        return D5S_COL_LABELS[col]
    c = str(col).strip().lower()
    em = D5SA_EXPLICIT_YEAR_COL_RE.match(c)
    if em:
        return f"{em.group(1).capitalize()} {em.group(2)} · {em.group(3)}S"
    em2 = D5SA_MONTH_COL_RE.match(c)
    if em2:
        mon, sn = em2.group(1), em2.group(2)
        yy = D5SA_MONTH_DEFAULT_YEAR.get(mon, "")
        yy_s = f" {yy}" if yy else ""
        return f"{mon.capitalize()}{yy_s} · {sn}S"
    return str(col)


def d5sa_max_reached_s_level_for_row_month_year(row, month_cols):
    """Highest S (1–5) among month_cols where this row has a star score."""
    best = 0
    for col in month_cols:
        lvl = d5sa_s_level_from_column_name(col)
        if not lvl:
            continue
        if d5sa_stars_to_score(row.get(col, "")) is not None:
            best = max(best, lvl)
    return best


def read_d5sa_audit_scoring_csv():
    if not os.path.exists(D5S_AUDIT_SCORING_CSV):
        return None
    df = pd.read_csv(D5S_AUDIT_SCORING_CSV, dtype=str, encoding="utf-8-sig")
    return df.fillna("")


def d5sa_stars_to_score(raw):
    if raw is None or (isinstance(raw, float) and pd.isna(raw)):
        return None
    t = str(raw).strip()
    if not t or t in ("–", "-", "—"):
        return None
    n = t.count("★")
    return n if n > 0 else None


def d5sa_build_milestone_model_levels_chart(month_value):
    """Horizontal bars: each model area vs highest 1S–5S reached for the month (0 = no score)."""
    if not month_value:
        return d5sa_empty_fig("Select a month for the milestone chart.")

    df = read_d5sa_audit_scoring_csv()
    if df is None or df.empty:
        return d5sa_empty_fig("No audit scoring data.")

    m, yyr = d5sa_split_month_year_value(month_value)
    if not m or yyr is None:
        return d5sa_empty_fig("Select a month for the milestone chart.")

    month_cols = d5sa_list_score_columns_for_month_year(df, m, yyr)
    if not month_cols:
        return d5sa_empty_fig(f"No score columns for “{m.capitalize()} {yyr}” in the CSV.")

    mly = f"{m.capitalize()} {yyr}"
    color_map = {
        5: "#15803d",
        4: "#22c55e",
        3: "#84cc16",
        2: "#eab308",
        1: "#f97316",
        0: "#94a3b8",
    }

    rows = []
    for _, r in df.iterrows():
        lvl = d5sa_max_reached_s_level_for_row_month_year(r, month_cols)
        rows.append(
            {
                "model": str(r["model_area"]).strip(),
                "zone": str(r["zone"]).strip(),
                "level": lvl,
            }
        )
    plot_df = pd.DataFrame(rows)
    plot_df = plot_df.sort_values(
        by=["level", "model"], ascending=[False, True]
    ).reset_index(drop=True)

    x_vals = []
    bar_text = []
    custom_zone = []
    custom_level_label = []
    colors = []
    for _, pr in plot_df.iterrows():
        lvl = int(pr["level"])
        colors.append(color_map.get(lvl, "#94a3b8"))
        if lvl > 0:
            x_vals.append(float(lvl))
            bar_text.append(f"{lvl}S")
            custom_level_label.append(f"{lvl}S (highest column with a star score)")
        else:
            x_vals.append(0.25)
            bar_text.append("—")
            custom_level_label.append("No numeric score for this month")
        custom_zone.append(pr["zone"])

    fig = go.Figure(
        go.Bar(
            x=x_vals,
            y=plot_df["model"],
            orientation="h",
            marker_color=colors,
            text=bar_text,
            textposition="outside",
            customdata=list(zip(custom_zone, custom_level_label)),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Zone: %{customdata[0]}<br>"
                "%{customdata[1]}<br>"
                f"<i>Month: {mly}</i><extra></extra>"
            ),
        )
    )
    n = len(plot_df)
    fig.update_layout(
        title=f"Highest S level reached by model area — {mly}",
        xaxis=dict(
            title="Highest S level reached",
            range=[0, 5.85],
            dtick=1,
            tick0=1,
            tickmode="linear",
            tickvals=[1, 2, 3, 4, 5],
            ticktext=["1S", "2S", "3S", "4S", "5S"],
        ),
        yaxis=dict(title="", automargin=True, tickfont=dict(size=10)),
        margin=dict(l=10, r=80, t=60, b=50),
        height=max(380, min(1400, 14 * n + 120)),
        showlegend=False,
        bargap=0.35,
        uirevision="d5sa-milestone-hbar",
    )
    fig.update_yaxes(autorange="reversed")
    return fig


def d5sa_level_to_label(lvl):
    if lvl <= 0:
        return "— (no score)"
    return f"{lvl}S"


def d5sa_build_zone_model_count_figure(month_value):
    """Bar chart: each zone vs count of distinct model areas (for selected audit month columns context)."""
    if not month_value:
        return d5sa_empty_fig("Select a month using the Month control above.")

    df = read_d5sa_audit_scoring_csv()
    if df is None or df.empty:
        return d5sa_empty_fig("No audit scoring data.")

    m, yyr = d5sa_split_month_year_value(month_value)
    if not m or yyr is None:
        return d5sa_empty_fig("Select a month using the Month control above.")

    month_cols = d5sa_list_score_columns_for_month_year(df, m, yyr)
    if not month_cols:
        return d5sa_empty_fig(f"No score columns for “{m.capitalize()} {yyr}” in the CSV.")

    mly = f"{m.capitalize()} {yyr}"

    z = df["zone"].astype(str).str.strip()
    ma = df["model_area"].astype(str).str.strip()
    plot_df = df.assign(_z=z, _ma=ma)
    counts = plot_df.groupby("_z", as_index=False).agg(n=("_ma", "nunique"))
    counts = counts[counts["_z"] != ""].sort_values("_z", ignore_index=True)

    if counts.empty:
        return d5sa_empty_fig("No zones to plot.")

    y_max = max(int(counts["n"].max()), 0)
    # Avoid dtick=1 with many levels in a short plot (labels overlap). Use coarser steps.
    if y_max <= 6:
        y_dtick = 1
    elif y_max <= 14:
        y_dtick = 2
    elif y_max <= 30:
        y_dtick = 5
    else:
        y_dtick = max(5, int(round(y_max / 10)))

    y_tick_steps = len(range(0, y_max + y_dtick, y_dtick)) if y_max > 0 else 2
    min_height_for_ticks = 120 + y_tick_steps * 26

    fig = go.Figure(
        go.Bar(
            x=counts["_z"].tolist(),
            y=counts["n"].tolist(),
            marker_color="#2563eb",
            hovertemplate=(
                "<b>%{x}</b><br>"
                "Model areas: %{y}<br>"
                "<i>Click bar for S-level list</i><extra></extra>"
            ),
        )
    )
    n_z = len(counts)
    base_h = max(300, min(720, 60 + 28 * n_z))
    fig_h = min(900, max(base_h, min_height_for_ticks))
    fig.update_layout(
        title=f"Zone vs number of model areas — {mly}",
        xaxis=dict(title="Zone", tickangle=-35, automargin=True),
        yaxis=dict(
            title=dict(text="Number of model areas", standoff=14),
            rangemode="tozero",
            tickmode="linear",
            tick0=0,
            dtick=y_dtick,
            automargin=True,
            tickfont=dict(size=12),
            showgrid=True,
            gridwidth=1,
            griddash="dot",
        ),
        margin=dict(l=72, r=20, t=55, b=max(80, min(200, 8 * n_z))),
        height=fig_h,
        showlegend=False,
        uirevision=f"d5sa-zone-count-{mly}",
    )
    return fig


def d5sa_build_zone_model_s_detail(zone: str, month_value: str):
    """HTML table: model areas in zone with highest S reached for the month."""
    if not zone or not month_value:
        return html.P("Missing zone or month.", className="text-muted small mb-0")

    df = read_d5sa_audit_scoring_csv()
    if df is None or df.empty:
        return dbc.Alert("No audit scoring data.", color="warning", className="mb-0")

    m, yyr = d5sa_split_month_year_value(month_value)
    if not m or yyr is None:
        return html.P("Missing month selection.", className="text-muted small mb-0")

    month_cols = d5sa_list_score_columns_for_month_year(df, m, yyr)
    mly = f"{m.capitalize()} {yyr}"
    if not month_cols:
        return dbc.Alert(
            f"No score columns for {d5sa_hov(mly)} in the CSV.",
            color="warning",
            className="mb-0",
        )
    sub = df[df["zone"].astype(str).str.strip() == zone].copy()
    if sub.empty:
        return dbc.Alert(f"No rows for zone “{d5sa_hov(zone)}”.", color="info", className="mb-0")

    rows_out = []
    for _, r in sub.iterrows():
        lvl = d5sa_max_reached_s_level_for_row_month_year(r, month_cols)
        rows_out.append(
            (
                str(r["model_area"]).strip(),
                lvl,
            )
        )
    rows_out.sort(key=lambda x: (-x[1], x[0].lower()))

    header = html.Thead(
        html.Tr(
            [
                html.Th("Model area"),
                html.Th(f"Highest S ({mly})"),
            ]
        )
    )
    body_rows = [
        html.Tr([html.Td(d5sa_hov(name)), html.Td(d5sa_level_to_label(lvl))])
        for name, lvl in rows_out
    ]
    caption = html.P(
        f"Zone: {d5sa_hov(zone)} · {len(rows_out)} model area(s). "
        "Highest S is the highest 1S–5S column for that month with a star score.",
        className="text-muted small mb-2",
    )
    return html.Div(
        [
            caption,
            dbc.Table(
                [header, html.Tbody(body_rows)],
                bordered=True,
                hover=True,
                size="sm",
                className="mb-0",
            ),
        ]
    )


def d5sa_zone_month_cols_for_audit_selection(df, month_select_value):
    """Score columns for the month+year encoded in milestone dropdown value (e.g. march:2026)."""
    m, y = d5sa_split_month_year_value(month_select_value)
    if not m or y is None:
        return []
    return d5sa_list_score_columns_for_month_year(df, m, y)


def d5sa_hov(s):
    return html_stdlib.escape(str(s), quote=False)


def d5sa_build_zone_hover_html_audit_month(zone, month_label, month_cols):
    """Hover for Zone vs Month when driven by audit month (all S columns for that month)."""
    df = read_d5sa_audit_scoring_csv()
    if df is None or not month_cols:
        return "No data."

    sub = df[df["zone"].astype(str).str.strip() == str(zone).strip()]
    lines = [
        f"<b>Zone:</b> {d5sa_hov(zone)}",
        f"<b>Month:</b> {d5sa_hov(month_label)} (all S columns with data)",
    ]
    any_scores = False
    for col in month_cols:
        scores = []
        raws = []
        for _, r in sub.iterrows():
            raw = str(r.get(col, "")).strip()
            sc = d5sa_stars_to_score(raw)
            if sc is not None:
                scores.append(sc)
                raws.append((str(r["model_area"]).strip(), raw, sc))
        col_label = d5sa_human_column_label(col)
        if scores:
            any_scores = True
            avg = sum(scores) / len(scores)
            lines.append(
                f"<b>{d5sa_hov(col_label)}:</b> mean {avg:.2f} / 5 ({len(scores)} areas)"
            )
            for name, raw, s in sorted(raws, key=lambda x: x[0])[:15]:
                lines.append(
                    f"  • {d5sa_hov(name)}: {d5sa_hov(raw)} ({s}/5)"
                )
            if len(raws) > 15:
                lines.append(f"  … and {len(raws) - 15} more for this column.")
        else:
            lines.append(f"<b>{d5sa_hov(col_label)}:</b> no numeric scores")
    if not any_scores:
        lines.append("No scored entries for this zone and month.")
    return "<br>".join(lines)


def d5sa_resolve_visible_columns(active_tab, selected_months):
    """Returns (cols, error_ui) where error_ui is a dbc.Alert or None."""
    tab = active_tab if active_tab in D5S_TAB_COLUMNS else "1S"
    base_cols = D5S_TAB_COLUMNS[tab]

    if selected_months is None:
        cols = base_cols
    elif len(selected_months) == 0:
        return None, dbc.Alert(
            "Select at least one month to show scoring columns.",
            color="info",
            className="mb-0",
        )
    else:
        sel = {str(m).lower() for m in selected_months}
        cols = [c for c in base_cols if D5S_COLUMN_MONTH.get(c) in sel]
        if not cols:
            return None, dbc.Alert(
                "No columns match the selected months for this S category.",
                color="warning",
                className="mb-0",
            )

    return cols, None


def d5sa_build_audit_scoring_table(active_tab, selected_months):
    cols, err = d5sa_resolve_visible_columns(active_tab, selected_months)
    if err is not None:
        return err

    df = read_d5sa_audit_scoring_csv()
    if df is None:
        return dbc.Alert(
            f"Audit scoring data file not found: {D5S_AUDIT_SCORING_CSV}",
            color="warning",
            className="mb-0",
        )
    missing = [c for c in cols if c not in df.columns]
    if missing:
        return dbc.Alert(
            "Audit scoring CSV is missing expected columns: " + ", ".join(missing),
            color="danger",
            className="mb-0",
        )
    show = df[["sl_no", "model_area", "zone"] + cols].copy()
    header_cells = [
        html.Th("Sl No"),
        html.Th("Model Area"),
        html.Th("Zone"),
    ] + [html.Th(D5S_COL_LABELS[c]) for c in cols]
    header = html.Thead(html.Tr(header_cells))
    body_rows = []
    for _, row in show.iterrows():
        body_rows.append(
            html.Tr(
                [
                    html.Td(row["sl_no"]),
                    html.Td(row["model_area"]),
                    html.Td(row["zone"]),
                ]
                + [html.Td(row[c]) for c in cols]
            )
        )
    return dbc.Table(
        [header, html.Tbody(body_rows)],
        bordered=True,
        hover=True,
        responsive=True,
        size="sm",
        className="mb-0",
    )


def d5sa_empty_fig(message):
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
    )
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=280)
    return fig


def d5sa_build_zone_month_figure(audit_month_value):
    """Zone vs Month for the selected audit month (all S score columns for that month)."""
    if not audit_month_value:
        return d5sa_empty_fig(
            "Select a month using the Month control at the top of this page."
        )

    m, yyr = d5sa_split_month_year_value(audit_month_value)
    if not m or yyr is None:
        return d5sa_empty_fig(
            "Select a month using the Month control at the top of this page."
        )

    df = read_d5sa_audit_scoring_csv()
    if df is None or df.empty:
        return d5sa_empty_fig("No data.")

    month_cols = d5sa_zone_month_cols_for_audit_selection(df, audit_month_value)
    if not month_cols:
        return d5sa_empty_fig(f"No score columns for “{m.capitalize()} {yyr}” in the CSV.")

    mlabel = f"{m.capitalize()} {yyr}"
    rows = []
    for col in month_cols:
        for _, r in df.iterrows():
            sc = d5sa_stars_to_score(r.get(col, ""))
            if sc is not None:
                rows.append(
                    {"zone": str(r["zone"]).strip(), "month": mlabel, "score": sc}
                )
    if not rows:
        return d5sa_empty_fig("No numeric scores for this view.")

    agg = (
        pd.DataFrame(rows)
        .groupby(["zone", "month"], as_index=False)
        .agg(score=("score", "mean"))
    )
    zones = sorted(agg["zone"].unique())
    month_order = [mlabel]

    fig = go.Figure()
    for zone in zones:
        y_vals = []
        hover_htmls = []
        for mo in month_order:
            sub = agg[(agg["zone"] == zone) & (agg["month"] == mo)]
            if len(sub):
                y_vals.append(round(float(sub["score"].iloc[0]), 2))
            else:
                y_vals.append(None)
            hover_htmls.append(
                d5sa_build_zone_hover_html_audit_month(zone, mo, month_cols)
            )

        fig.add_trace(
            go.Bar(
                name=zone,
                x=month_order,
                y=y_vals,
                customdata=hover_htmls,
                hovertemplate="%{customdata}<extra></extra>",
            )
        )

    fig.update_layout(
        title=f"Zone vs Month (mean score / 5) — {mlabel}",
        barmode="group",
        legend_title="Zone",
        margin=dict(l=40, r=20, t=50, b=40),
        height=400,
        yaxis=dict(range=[0, 5.5], title="Mean ★ score"),
        xaxis=dict(title="Month"),
        uirevision="d5sa-zone",
    )
    return fig


layout = dbc.Container(
    [
        dcc.Store(id="d5sa-audit-scoring-init", data=1),
        html.H2("Summary"),
        html.P(
            "Data from Data/5S.csv.",
            className="text-muted small mb-1",
        ),
        html.P(
            "November and December (plain column names such as november_1s) are calendar year 2025; "
            "February and March are 2026. Add later Nov/Dec scores as november_2026_1s, december_2026_2s, etc.",
            className="text-muted small mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Year"),
                        dcc.Dropdown(
                            id="d5sa-summary-year-select",
                            options=[{"label": str(y), "value": y} for y in (2025, 2026, 2027)],
                            value=2026,
                            clearable=False,
                            className="mb-2",
                        ),
                    ],
                    md=3,
                ),
                dbc.Col(
                    [
                        html.Label("Month"),
                        dcc.Dropdown(
                            id="d5sa-milestone-month-select",
                            options=[],
                            value=None,
                            clearable=False,
                            placeholder="Select month…",
                            className="mb-2",
                        ),
                    ],
                    md=5,
                ),
            ],
            className="mb-1",
        ),
        html.H5("Zone vs number of model areas", className="mt-2 mb-2"),
        html.P(
            "Choose Year and Month above. "
            "Click a zone bar to list every model area in that zone and the highest 1S–5S level "
            "reached for that month (same rule as the milestone chart).",
            className="text-muted small mb-2",
        ),
        dcc.Graph(
            id="d5sa-zone-model-count-graph",
            className="mb-2",
            config={"displayModeBar": True},
        ),
        html.Div(
            id="d5sa-zone-model-count-detail",
            className="mb-3 p-2",
            style={
                "border": "1px solid #dee2e6",
                "borderRadius": "4px",
                "backgroundColor": "#f8fafc",
                "minHeight": "48px",
            },
        ),
        html.H5("Highest S level reached (by model area)", className="mt-2 mb-2"),
        html.P(
            "Uses the Year and Month selected above. Each bar is one model area; length shows the highest "
            "S column (5S → 1S) that has a star rating that month. Labels show 1S…5S (— = no score).",
            className="text-muted small mb-2",
        ),
        dcc.Graph(
            id="d5sa-milestone-model-levels-graph",
            className="mb-3",
            config={"displayModeBar": True},
        ),
        html.H5("Zone vs Month (mean score / 5)", className="mt-2 mb-2"),
        html.P(
            "Uses the Year and Month controls at the top of this page. Bars aggregate mean star scores "
            "across every S column present in the CSV for that calendar month.",
            className="text-muted small mb-2",
        ),
        dcc.Graph(
            id="d5sa-zone-month-graph",
            className="mb-4",
            config={"displayModeBar": True},
        ),
        html.H5("Data table", className="mb-2"),
        html.P(
            "Choose S category (1S–5S) and months to control which columns appear in the table.",
            className="text-muted small mb-2",
        ),
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label("Months"),
                        dcc.Dropdown(
                            id="d5sa-month-filter",
                            options=[],
                            value=None,
                            multi=True,
                            placeholder="Select months…",
                            className="mb-3",
                        ),
                    ],
                    md=6,
                ),
            ],
            className="mb-1",
        ),
        dbc.Tabs(
            id="d5sa-audit-s-tabs",
            active_tab="1S",
            children=[
                dbc.Tab(label="1S", tab_id="1S"),
                dbc.Tab(label="2S", tab_id="2S"),
                dbc.Tab(label="3S", tab_id="3S"),
                dbc.Tab(label="4S", tab_id="4S"),
                dbc.Tab(label="5S", tab_id="5S"),
            ],
            className="mb-2",
        ),
        html.Div(
            id="d5sa-audit-scoring-content",
            className="p-2",
            style={
                "border": "1px solid #dee2e6",
                "borderRadius": "4px",
                "backgroundColor": "#fff",
            },
        ),
    ],
    fluid=True,
)


@callback(
    Output("d5sa-zone-model-count-graph", "figure"),
    Input("d5sa-milestone-month-select", "value"),
)
def d5sa_render_zone_model_count_figure(audit_month):
    return d5sa_build_zone_model_count_figure(audit_month)


@callback(
    Output("d5sa-zone-model-count-detail", "children"),
    Input("d5sa-zone-model-count-graph", "clickData"),
    Input("d5sa-milestone-month-select", "value"),
    Input("d5sa-summary-year-select", "value"),
)
def d5sa_render_zone_model_count_click_detail(click_data, audit_month, _year):
    if not audit_month:
        return html.P(
            "Select Year and Month using the controls above.",
            className="text-muted small mb-0",
        )
    trig = ctx.triggered_id
    if trig in ("d5sa-milestone-month-select", "d5sa-summary-year-select"):
        lab = d5sa_milestone_selection_label(audit_month)
        return html.P(
            f"Selection: {lab}. Click a zone bar in the chart above "
            "to list each model area and its highest S level for that period.",
            className="text-muted small mb-0",
        )
    if trig == "d5sa-zone-model-count-graph" and click_data and click_data.get("points"):
        zone = str(click_data["points"][0].get("x", "")).strip()
        if zone:
            return d5sa_build_zone_model_s_detail(zone, audit_month)
    lab = d5sa_milestone_selection_label(audit_month)
    return html.P(
        f"Selection: {lab}. Click a zone bar in the chart above "
        "to see model areas and S levels.",
        className="text-muted small mb-0",
    )


@callback(
    Output("d5sa-month-filter", "options"),
    Output("d5sa-month-filter", "value"),
    Input("d5sa-audit-s-tabs", "active_tab"),
)
def d5sa_sync_month_dropdown_for_s_tab(active_tab):
    tab = active_tab if active_tab in D5S_TAB_COLUMNS else "1S"
    cols = D5S_TAB_COLUMNS[tab]
    present = []
    for m in D5SA_MONTH_ORDER:
        if any(D5S_COLUMN_MONTH[c] == m for c in cols):
            present.append(m)
    opts = [{"label": m.capitalize(), "value": m} for m in present]
    return opts, present


@callback(
    Output("d5sa-audit-scoring-content", "children"),
    Input("d5sa-audit-s-tabs", "active_tab"),
    Input("d5sa-month-filter", "value"),
)
def d5sa_update_audit_scoring_table(active_tab, selected_months):
    return d5sa_build_audit_scoring_table(active_tab, selected_months)




@callback(
    Output("d5sa-zone-month-graph", "figure"),
    Input("d5sa-milestone-month-select", "value"),
)
def d5sa_update_zone_month_from_audit_month(audit_month):
    return d5sa_build_zone_month_figure(audit_month)


@callback(
    Output("d5sa-milestone-month-select", "options"),
    Output("d5sa-milestone-month-select", "value"),
    Input("d5sa-audit-scoring-init", "data"),
    Input("d5sa-summary-year-select", "value"),
)
def d5sa_refresh_milestone_month_dropdown(_init, selected_year):
    df = read_d5sa_audit_scoring_csv()
    pairs = d5sa_discover_month_year_pairs_in_df(df)
    ysel = int(selected_year) if selected_year is not None else 2026
    filtered = [(m, yy) for (m, yy) in pairs if yy == ysel]
    opts = [{"label": f"{m.capitalize()} {yy}", "value": f"{m}:{yy}"} for m, yy in filtered]
    if not filtered:
        return [], None
    ordered = d5sa_sort_month_year_pairs(set(pairs))
    default_pair = None
    for p in reversed(ordered):
        if p in filtered:
            default_pair = p
            break
    if default_pair is None:
        default_pair = filtered[-1]
    default_val = f"{default_pair[0]}:{default_pair[1]}"
    return opts, default_val


@callback(
    Output("d5sa-milestone-model-levels-graph", "figure"),
    Input("d5sa-milestone-month-select", "value"),
)
def d5sa_update_milestone_model_levels_graph(selected_month):
    return d5sa_build_milestone_model_levels_chart(selected_month)
