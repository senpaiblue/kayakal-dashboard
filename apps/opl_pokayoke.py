import dash
from app import app
import pandas as pd
import datetime as dt
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, callback_context
from dash import dash_table
import plotly.express as px
from apps import analysis,events,reports,gallery,summary
import dash_bootstrap_components as dbc
from flask_caching import Cache
cache = Cache(app.server, config={"CACHE_TYPE": "simple"})
from dash import callback_context as ctx

# ---------------- CONFIG ----------------
CSV_PATH = "./Data/opl_pokayoke.csv"
DATE_COL = "TransactionDate"
EXCLUDED_STATUS = ["Saved as Draft"]

def opl_apply_modern_bar_style(fig, title=None):
    fig.update_layout(
        title=dict(
            text=title,
            x=0.02,
            y=0.95,
            font=dict(size=16, family="Segoe UI", color="#0f172a")
        ) if title else None,

        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",

        margin=dict(l=30, r=20, t=50, b=30),

        xaxis=dict(
            showgrid=False,
            tickfont=dict(size=12),
            linecolor="rgba(0,0,0,0)"
        ),

        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(203,213,225,0.6)",
            tickfont=dict(size=12),
            zeroline=False
        ),

        hovermode="x unified",
        font=dict(family="Segoe UI, Arial")
    )

    fig.update_traces(
        marker=dict(
            line=dict(width=0),
            opacity=0.95
        ),
        hoverlabel=dict(
            bgcolor="rgba(15,23,42,0.9)",
            font_size=13,
            font_color="white"
        )
    )

    return fig


# ---------------- DATA LOADING ----------------
def opl_read_csv_safely(path):
    for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except:
            pass
    raise UnicodeDecodeError("Unable to read CSV")

def opl_load_df():
    # Load CSV
    df = opl_read_csv_safely(CSV_PATH)
    df.columns = df.columns.str.strip()
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")

    # Rename departments for OPL/Poka Yoke page ONLY
    if "Department" in df.columns:
        # Strip whitespace and newline characters that may exist in raw data
        df["Department"] = df["Department"].astype(str).str.strip()
        # Merge renamed department data into single canonical label.
        df["Department"] = df["Department"].str.replace(
            r"(?i)^Logistics_Deleted$",
            "Logistics",
            regex=True,
        )
        # 1. Bar Mill II
        df["Department"] = df["Department"].str.replace(r'\b(?:BRM 2|BRM2)\b', 'Bar Mill II', case=False, regex=True)
        # 2. Bar Rod Mill I
        df["Department"] = df["Department"].str.replace(r'\b(?:BRM I|BRM 1|BRM1)\b', 'Bar Rod Mill I', case=False, regex=True)
        # 3. Blast Furnace
        df["Department"] = df["Department"].str.replace(r'(?i)Blast Furnace\s*(?:I\s*&\s*II|-1,2|1\s*&\s*2)', 'Blast Furnace I ,Blast Furnace II', regex=True)
        # 4. Coke Ovens
        df["Department"] = df["Department"].str.replace(r'\b(?:Coke Oven V|Coke Oven 5)\b', 'Coke Ovens V', case=False, regex=True)
        df["Department"] = df["Department"].str.replace(r'\b(?:Coke Oven IV|Coke Oven 4)\b', 'Coke Ovens IV', case=False, regex=True)
        # 5. Hot Strip Mill
        df["Department"] = df["Department"].str.replace(r'\b(?:HSM II|HSM 2|HSM2)\b', 'Hot Strip Mill II', case=False, regex=True)
        df["Department"] = df["Department"].str.replace(r'\b(?:HSM I|HSM 1|HSM1)\b', 'Hot Strip Mill I', case=False, regex=True)
        # Cold Rolling Mill
        df["Department"] = df["Department"].str.replace(r'\b(?:CRM II|CRM 2|CRM2)\b', 'Cold Rolling Mill II', case=False, regex=True)
        df["Department"] = df["Department"].str.replace(r'\b(?:CRM I|CRM 1|CRM1)\b', 'Cold Rolling Mill I', case=False, regex=True)
        # 6. Wire Rod Mill II
        df["Department"] = df["Department"].str.replace(r'\b(?:WRM II|WRM 2|WRM2|WRM-2|WRM\s*#2)\b', 'Wire Rod Mill II', case=False, regex=True)
        # 7. Wire Rod Mill I
        df["Department"] = df["Department"].str.replace(r'\b(?:WRM I|WRM 1|WRM1)\b', 'Wire Rod Mill I', case=False, regex=True)
        df["Department"] = df["Department"].str.replace(r'^\s*WRM\s*$', 'Wire Rod Mill I', case=False, regex=True)
        # 8. RMHS
        df["Department"] = df["Department"].str.replace(r'(?i)RMHS\s*Upto\s*(?:10|5|7)\s*MT', 'Raw Material Handling System', regex=True)

    return df

df = opl_load_df()

today = dt.date.today()
default_start = today - dt.timedelta(days=29)
default_end = today

# ---------------- SHARED STYLE ----------------
graph_card_style = {
    "width": "100%",
    "boxSizing": "border-box",
    "border": "1px solid #d0d7de",
    "borderRadius": "8px",
    "padding": "8px",
    "backgroundColor": "#fff",
    "marginBottom": "16px",
}
graph_height_standard = "400px"
graph_height_tall = "460px"  # many x-axis categories (departments)

# ---------------- LAYOUT ----------------
layout = html.Div([

    # -------- Department Filter --------
    html.Div([
        html.Label("Select Department:", style={"fontWeight": "600"}),
        dcc.Dropdown(
            id="opl_dept_filter",
            options=[{"label": "Overall", "value": "Overall"}] +
                    [{"label": d, "value": d} for d in sorted(df["Department"].dropna().unique())],
            value="Overall",
            clearable=False,
            style={"width": "300px"}
        )
    ], style={"marginBottom": "15px"}),

    # -------- Financial Year Section (stacked full width) --------
    html.Div([
        html.Div(
            dcc.Graph(id="opl_fy_yearly_graph", style={"height": graph_height_standard}),
            style=graph_card_style,
        ),
        html.Div(
            dcc.Graph(id="opl_fy_monthly_graph", style={"height": graph_height_standard}),
            style=graph_card_style,
        ),
        html.Div(
            dcc.Graph(id="opl_bar_dept_alltime", style={"height": graph_height_tall}),
            style={**graph_card_style, "marginBottom": "12px"},
        ),
    ]),

    # -------- Target Graphs Section (for FY27) --------
    html.Div(id="opl_target_graphs_container", style={"display": "none"}),

    # -------- Date Picker --------
    html.Div([
        html.Label("Select Date Range:", style={"fontWeight": "600"}),
        dcc.DatePickerRange(
            id="opl_date_range",
            min_date_allowed=df[DATE_COL].min().date() if not df.empty and not df[DATE_COL].isna().all() else default_start,
            max_date_allowed=dt.date.today(),
            start_date=default_start,
            end_date=default_end,
            display_format="DD-MM-YYYY",
            clearable=False
        )
    ], style={"margin": "15px 0"}),

    html.Div(id="opl_summary-text"),

    # =========================================================
    # 📊 OVERALL STATISTICS (STATIC – DATE RANGE BASED)
    # =========================================================
    html.H4("📊 Overall Statistics (Date Range Based)", style={"marginTop": "20px"}),

    html.Div([
        html.Div(
            dcc.Graph(id="opl_bar_dept_range", style={"height": graph_height_tall}),
            style=graph_card_style,
        ),
        html.Div(
            dcc.Graph(id="opl_bar_status", style={"height": graph_height_standard}),
            style=graph_card_style,
        ),
    ], style={"marginBottom": "12px"}),

    # =========================================================
    # 🖱 INTERACTIVE ANALYSIS (CLICK TO DRILL DOWN)
    # =========================================================
    html.H4("🖱 Interactive Analysis (Click to Drill Down)"),

    html.Div([
        html.Div(
            dcc.Graph(id="opl_bar_tic", style={"height": graph_height_standard}),
            style=graph_card_style,
        ),
        html.Div(
            dcc.Graph(id="opl_bar_dept", style={"height": graph_height_tall}),
            style={**graph_card_style, "marginBottom": "12px"},
        ),
    ], style={"marginBottom": "12px"}),

    # -------- Table + Leaderboard --------
    html.Div(id="opl_details_table", style={"marginTop": "15px"}),
    html.Div(id="opl_leaderboard-container", style={"marginTop": "15px"}),

], style={"padding": "20px", "fontFamily": "Arial"})


# ----------------- Callback 1: PIE charts (pie clicks affect only downstream pies) -----------------
def opl_hide_small_pie_labels(fig, threshold=2):
    for trace in fig.data:
        if trace.type == "pie":
            if trace.values is not None:
                values = list(trace.values)
            elif trace.customdata is not None:
                try:
                    values = [d[0] if isinstance(d, (list, tuple)) else d for d in trace.customdata]
                except:
                    continue
            else:
                continue

            total = sum(values)

            templates = []
            for v in values:
                pct = (v / total) * 100
                if pct < threshold:
                    templates.append("")  # hide
                else:
                    templates.append("%{label}: %{percent}")  # show

            trace.texttemplate = templates
            trace.textposition = "outside"

    return fig

def opl_pie_show_counts(fig):
    for trace in fig.data:
        if trace.type == "pie":
            trace.textinfo = "label+value"
            trace.hovertemplate = "%{label}: %{value}<extra></extra>"
    return fig

@app.callback(
    Output("opl_pie_dept_range", "figure"),
    Output("opl_pie_status", "figure"),
    Output("opl_pie_tic", "figure"),
    Output("opl_pie_dept", "figure"),
    Output("opl_summary-text", "children"), 

    Input("opl_date_range", "start_date"),
    Input("opl_date_range", "end_date"),
    Input("opl_pie_tic", "clickData"),
)
def opl_update_pies(start_date, end_date, pie_tic_click):
    df = opl_load_df()

    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]
    summary = f"Showing {len(base)} rows from {s:%d-%m-%Y} to {e:%d-%m-%Y}"

    # PIE 0 — Dept Range
    pie_dept_range_df = base.groupby("Department").size().reset_index(name="count")
    pie_dept_range = px.pie(
        pie_dept_range_df, names="Department", values="count",
        title="Dept Count (Selected Range)", hole=0.35
    )
    pie_dept_range.update_traces(textinfo="label+value")
    pie_dept_range.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font_color="white"
    )

    # PIE 1 — Status
    pie_status = px.pie(
        base.groupby("ID").size().reset_index(name="count"),
        names="ID", values="count",
        title="By OPL / Poka Yoke Status", hole=0.35
    )
    pie_status.update_traces(textinfo="label+value")
    pie_status.update_layout(
        paper_bgcolor="#1e1e1e",
        plot_bgcolor="#1e1e1e",
        font_color="white"
    )

    # PIE 2 — TIC
    pie_tic_df = base[~base["ID"].isin(EXCLUDED_STATUS)]
    pie_tic = px.pie(
        pie_tic_df.groupby("TICName").size().reset_index(name="count"),
        names="TICName", values="count",
        title="By TIC Name", hole=0.35
    )
    pie_tic.update_traces(textinfo="label+value")

    # PIE 3 — Department
    sel_tic = None
    if pie_tic_click and "points" in pie_tic_click:
        sel_tic = pie_tic_click["points"][0]["label"]

    pie_dept_df = pie_tic_df if not sel_tic else pie_tic_df[pie_tic_df["TICName"] == sel_tic]
    pie_dept = px.pie(
        pie_dept_df.groupby("Department").size().reset_index(name="count"),
        names="Department", values="count",
        title=f"By Department{(' • ' + sel_tic) if sel_tic else ''}",
        hole=0.35
    )
    pie_dept.update_traces(textinfo="label+value")

    return pie_dept_range, pie_status, pie_tic, pie_dept, summary


# ----------------- Callback 2: BAR charts (bar clicks affect only downstream bars) -----------------
@app.callback(
    Output("opl_bar_dept_range", "figure"),
    Output("opl_bar_status", "figure"),
    Output("opl_bar_tic", "figure"),
    Output("opl_bar_dept", "figure"),

    Input("opl_date_range", "start_date"),
    Input("opl_date_range", "end_date"),
    Input("opl_bar_tic", "clickData"),
)
def opl_update_bars(start_date, end_date, bar_tic_click):
    df = opl_load_df()

    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[
        (df[DATE_COL].dt.date >= s) &
        (df[DATE_COL].dt.date <= e)
    ]

    # BAR 0 — Dept Count
    bar_dep_df = (
        base.groupby("Department")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    bar_dept_range = px.bar(
        bar_dep_df,
        x="Department",
        y="count",
        text="count",
        title="Dept Count (Selected Range)"
    )
    bar_dept_range.update_traces(textposition="outside")
    bar_dept_range.update_layout(xaxis_tickangle=-45)

    if not bar_dep_df.empty:
        max_y = bar_dep_df["count"].max()
        bar_dept_range.update_yaxes(range=[0, max_y * 1.25])
    bar_dept_range = opl_apply_modern_bar_style(bar_dept_range)

    # BAR 1 — Status Count (using "ID" column)
    bar_status_df = (
        base.groupby("ID")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    bar_status = px.bar(
        bar_status_df,
        x="ID",
        y="count",
        text="count",
        title="Status Count"
    )
    bar_status.update_traces(textposition="outside")
    bar_status.update_layout(xaxis_tickangle=-30)

    if not bar_status_df.empty:
        max_y = bar_status_df["count"].max()
        bar_status.update_yaxes(range=[0, max_y * 1.25])
    bar_status = opl_apply_modern_bar_style(bar_status)

    # BAR 2 — TIC Name Count
    base_tic = base[~base["ID"].isin(EXCLUDED_STATUS)]
    bar_tic_df = (
        base_tic.groupby("TICName")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    bar_tic = px.bar(
        bar_tic_df,
        x="TICName",
        y="count",
        text="count",
        title="TIC Name Count"
    )
    bar_tic.update_traces(textposition="outside")
    bar_tic.update_layout(xaxis_tickangle=-45)

    if not bar_tic_df.empty:
        max_y = bar_tic_df["count"].max()
        bar_tic.update_yaxes(range=[0, max_y * 1.25])
    bar_tic = opl_apply_modern_bar_style(bar_tic)

    # BAR 3 — Department Count
    sel_tic = None
    if bar_tic_click and "points" in bar_tic_click:
        sel_tic = bar_tic_click["points"][0]["x"]

    dept_df = base_tic if not sel_tic else base_tic[base_tic["TICName"] == sel_tic]
    bar_dept_df = (
        dept_df.groupby("Department")
        .size()
        .reset_index(name="count")
        .sort_values("count", ascending=False)
    )

    bar_dept = px.bar(
        bar_dept_df,
        x="Department",
        y="count",
        text="count",
        title=f"Department Count{(' • ' + sel_tic) if sel_tic else ''}"
    )
    bar_dept.update_traces(textposition="outside")
    bar_dept.update_layout(xaxis_tickangle=-45)

    if not bar_dept_df.empty:
        max_y = bar_dept_df["count"].max()
        bar_dept.update_yaxes(range=[0, max_y * 1.25])
    bar_dept = opl_apply_modern_bar_style(bar_dept)

    return bar_dept_range, bar_status, bar_tic, bar_dept


# ----------------- Callback 3: Table (triggered only by bar_dept click) -----------------
@app.callback(
    Output("opl_details_table", "children"),
    Input("opl_bar_dept", "clickData"),
    Input("opl_date_range", "start_date"),
    Input("opl_date_range", "end_date"),
    Input("opl_bar_status", "clickData"),
    Input("opl_bar_tic", "clickData"),
)
def opl_update_table(bar3_click, start_date, end_date, bar1_click, bar2_click):
    df = opl_load_df()
    if not bar3_click or "points" not in bar3_click:
        return ""

    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]

    # Respect bar1 and bar2 context
    if bar1_click and "points" in bar1_click:
        v = bar1_click["points"][0].get("label") or bar1_click["points"][0].get("x")
        base = base[base["ID"] == v]

    if bar2_click and "points" in bar2_click:
        v = bar2_click["points"][0].get("label") or bar2_click["points"][0].get("x")
        base = base[base["TICName"] == v]

    # Final dept clicked
    dept_val = bar3_click["points"][0].get("label") or bar3_click["points"][0].get("x")
    base = base[base["Department"] == dept_val]

    if base.empty:
        return html.Div(f"No rows for Department '{dept_val}' in the selected date range.", style={"padding": "8px"})

    # Prepare table with date column included
    # OPL uses "Impact" instead of "KaizenImpact", and "Classification" instead of "KaizenCategory"
    table_df = base[[
        DATE_COL,
        "ImplementedByFirstPerson",
        "Emp1Code",
        "Emp1Grade",
        "Impact",
        "Classification"
    ]].rename(columns={
        DATE_COL: "Date",
        "ImplementedByFirstPerson": "Name of Emp",
        "Emp1Code": "Emp Code",
        "Emp1Grade": "Grade",
        "Impact": "Impact",
        "Classification": "Classification"
    }).fillna("")

    try:
        table_df["Date"] = pd.to_datetime(table_df["Date"]).dt.strftime("%d-%m-%Y")
    except Exception:
        pass

    dtbl = dash_table.DataTable(
        data=table_df.to_dict("records"),
        columns=[{"name": c, "id": c} for c in table_df.columns],
        page_size=12,
        style_table={"overflowX": "auto"},
        style_cell={"padding": "6px", "textAlign": "left", "whiteSpace": "normal"},
        style_header={"backgroundColor": "#f7f7f8", "fontWeight": "bold"},
    )

    return html.Div([
        html.H4(f"Rows for Department '{dept_val}'"),
        dtbl
    ], style={"padding": "8px", "border": "1px solid #d0d7de", "borderRadius": "6px", "backgroundColor": "#fff"})


# ----------------- Callback: Financial Year Bar Graphs -----------------
@app.callback(
    Output("opl_fy_yearly_graph", "figure"),
    Output("opl_fy_monthly_graph", "figure"),
    Output("opl_bar_dept_alltime", "figure"),

    Input("opl_dept_filter", "value"),
    Input("opl_fy_yearly_graph", "clickData"),
    Input("opl_fy_monthly_graph", "clickData"),
)
def opl_update_financial_year_graphs(selected_dept, fy_click, month_click):
    df = opl_load_df()
    dff = df.copy()

    if selected_dept != "Overall":
        dff = dff[dff["Department"] == selected_dept]

    # Add FY column
    dff["FY"] = dff[DATE_COL].apply(
        lambda d: f"FY-{(d.year + 1) if d.month >= 4 else d.year}" if d is not None and not pd.isna(d) else "Unknown"
    )

    # Detect trigger
    trig = callback_context.triggered[0]["prop_id"].split(".")[0] if callback_context.triggered else ""

    # Select FY
    if fy_click and "points" in fy_click:
        selected_fy = fy_click["points"][0]["x"]
    else:
        today = pd.Timestamp.today()
        current_fy = today.year + 1 if today.month >= 4 else today.year
        selected_fy = f"FY-{current_fy}"

    # 1. YEARLY GRAPH
    fy_yearly = dff.groupby("FY").size().reset_index(name="Count")
    fig_yearly = px.bar(
        fy_yearly,
        x="FY",
        y="Count",
        text="Count",
        title="Yearly Count by Financial Year"
    )

    fig_yearly.update_traces(
        marker_color=[
            "green" if fy == selected_fy else "#90EE90"
            for fy in fy_yearly["FY"]
        ],
        textposition="outside"
    )

    if not fy_yearly.empty:
        fig_yearly.update_yaxes(range=[0, fy_yearly["Count"].max() * 1.25])
    fig_yearly = opl_apply_modern_bar_style(fig_yearly)

    # 2. MONTHLY GRAPH
    dff_fy = dff[dff["FY"] == selected_fy].copy()
    dff_fy["Month"] = dff_fy[DATE_COL].dt.to_period("M").dt.to_timestamp()

    fy_month = (
        dff_fy
        .groupby("Month")
        .size()
        .reset_index(name="Count")
        .sort_values("Month")
    )

    if not fy_month.empty:
        fy_month["Month_Str"] = fy_month["Month"].dt.strftime("%b %Y")
    else:
        fy_month["Month_Str"] = []

    fig_month = px.bar(
        fy_month,
        x="Month_Str",
        y="Count",
        text="Count",
        title=f"Monthly Trend for {selected_fy}"
    )

    fig_month.update_traces(
        marker_color="#FFD580",
        marker_line_color="#FF8C00",
        textposition="outside"
    )

    if not fy_month.empty:
        fig_month.update_yaxes(range=[0, fy_month["Count"].max() * 1.25])
        fig_month.update_layout(
            xaxis=dict(
                type="category",
                categoryorder="array",
                categoryarray=fy_month["Month_Str"].tolist(),
                tickmode="array",
                tickvals=fy_month["Month_Str"].tolist(),
                ticktext=fy_month["Month_Str"].tolist()
            )
        )
    fig_month = opl_apply_modern_bar_style(fig_month)

    # 3. DEPARTMENT GRAPH
    dept_base = dff_fy.copy()

    # Apply MONTH filter if clicked
    if trig == "opl_fy_monthly_graph" and month_click and "points" in month_click:
        clicked_month = pd.to_datetime(month_click["points"][0]["x"])
        dept_base = dept_base[
            dept_base[DATE_COL].dt.to_period("M")
            == clicked_month.to_period("M")
        ]
        dept_title = f"Department Count • {clicked_month.strftime('%b-%Y')}"
    else:
        dept_title = f"Department Count • {selected_fy}"

    dept_df = (
        dept_base
        .groupby("Department")
        .size()
        .reset_index(name="Count")
        .sort_values("Count", ascending=False)
    )

    fig_dept = px.bar(
        dept_df,
        x="Department",
        y="Count",
        text="Count",
        title=dept_title
    )

    fig_dept.update_traces(textposition="outside")
    if not dept_df.empty:
        fig_dept.update_yaxes(range=[0, dept_df["Count"].max() * 1.25])
    fig_dept.update_layout(xaxis_tickangle=-45)
    fig_dept = opl_apply_modern_bar_style(fig_dept)

    return fig_yearly, fig_month, fig_dept


@app.callback(
    Output("opl_leaderboard-container", "children"),

    Input("opl_bar_dept_alltime", "clickData"),
    Input("opl_fy_yearly_graph", "clickData"),
    Input("opl_fy_monthly_graph", "clickData"),
    Input("opl_date_range", "start_date"),
    Input("opl_date_range", "end_date")
)
def opl_update_leaderboard(dept_click, fy_click, month_click, start_date, end_date):
    df = opl_load_df()
    dff = df.copy()

    # Apply FY filter
    dff["FY"] = dff[DATE_COL].apply(
        lambda d: f"FY-{(d.year + 1) if d.month >= 4 else d.year}" if d is not None and not pd.isna(d) else "Unknown"
    )

    if fy_click and "points" in fy_click:
        selected_fy = fy_click["points"][0]["x"]
    else:
        today = pd.Timestamp.today()
        current_fy = today.year + 1 if today.month >= 4 else today.year
        selected_fy = f"FY-{current_fy}"

    dff = dff[dff["FY"] == selected_fy]
    
    # Apply Month filter
    if month_click and "points" in month_click:
        clicked_month = pd.to_datetime(month_click["points"][0]["x"])
        dff = dff[
            dff[DATE_COL].dt.to_period("M")
            == clicked_month.to_period("M")
        ]

    # Department Click filter
    if dept_click and "points" in dept_click:
        dept_val = dept_click["points"][0].get("x")
        dff = df[df["Department"] == dept_val]
        title = f"Top 10 Contributors (All Time • {dept_val})"
    else:
        try:
            s = pd.to_datetime(start_date).date()
            e = pd.to_datetime(end_date).date()
        except:
            s, e = default_start, default_end

        dff = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]
        title = "Top 10 Contributors (Date Range)"

    grouped = (
        dff.groupby(["Emp1Code", "ImplementedByFirstPerson", "Department"])
           .size()
           .reset_index(name="count")
           .sort_values("count", ascending=False)
           .head(10)
           .reset_index(drop=True)
    )

    items = []
    for idx, row in grouped.iterrows():
        rank = idx + 1
        items.append(
            html.Div([
                html.Div(f"{rank}", className="leader-rank"),
                html.Div([
                    html.Div(f"{row['ImplementedByFirstPerson']} ({row['Emp1Code']})"),
                    html.Div(f"Department: {row['Department']}")
                ], className="leader-text"),
                html.Div(f"{row['count']}", className="leader-score")
            ], className="leader-item")
        )

    return [
        html.Div(title, className="leaderboard-title"),
        *items
    ]


# ----------------- Callback: Target Analysis for FY27 -----------------
@app.callback(
    Output("opl_target_graphs_container", "children"),
    Output("opl_target_graphs_container", "style"),
    Input("opl_dept_filter", "value"),
    Input("opl_fy_yearly_graph", "clickData"),
    Input("opl_fy_monthly_graph", "clickData"),
)
def opl_update_target_graphs(selected_dept, fy_click, month_click):
    # Determine the active financial year
    if fy_click and "points" in fy_click:
        selected_fy = fy_click["points"][0]["x"]
    else:
        today = pd.Timestamp.today()
        current_fy = today.year + 1 if today.month >= 4 else today.year
        selected_fy = f"FY-{current_fy}"

    if selected_fy != "FY-2027":
        return None, {"display": "none"}

    import plotly.graph_objects as go

    try:
        target_df = pd.read_csv("./Data/Target Index.csv")
    except Exception as e:
        return html.Div(f"Error loading Target Index: {str(e)}"), {"display": "block"}

    # Clean target dataframe
    target_df = target_df.dropna(subset=["Unnamed: 3"])
    target_df["Unnamed: 3"] = target_df["Unnamed: 3"].astype(str).str.strip()
    
    # OPL specific targets
    target_df["OPL/POKA YOKE YearlyTarget"] = pd.to_numeric(target_df["OPL/POKA YOKE YearlyTarget"], errors="coerce").fillna(0).astype(int)
    target_df["OPL/POKA YOKE Monthly Target"] = pd.to_numeric(target_df["OPL/POKA YOKE Monthly Target"], errors="coerce").fillna(0.0).astype(float)
    target_depts = target_df["Unnamed: 3"].tolist()

    # Load actuals
    df_act = opl_load_df()
    df_act["FY"] = df_act[DATE_COL].apply(
        lambda d: f"FY-{(d.year + 1) if d.month >= 4 else d.year}" if d is not None and not pd.isna(d) else "Unknown"
    )
    df_fy27 = df_act[df_act["FY"] == "FY-2027"].copy()

    # Map month string
    month_mapping = {
        (2026, 4): "Apr 2026", (2026, 5): "May 2026", (2026, 6): "Jun 2026",
        (2026, 7): "Jul 2026", (2026, 8): "Aug 2026", (2026, 9): "Sep 2026",
        (2026, 10): "Oct 2026", (2026, 11): "Nov 2026", (2026, 12): "Dec 2026",
        (2027, 1): "Jan 2027", (2027, 2): "Feb 2027", (2027, 3): "Mar 2027"
    }
    df_fy27["Month_Str"] = df_fy27[DATE_COL].apply(
        lambda d: month_mapping.get((d.year, d.month), None) if d is not None and not pd.isna(d) else None
    )

    # Determine if a month in FY-2027 was clicked
    clicked_month = None
    if month_click and "points" in month_click:
        clicked_x = month_click["points"][0]["x"]
        valid_months_for_fy27 = [
            "Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026",
            "Oct 2026", "Nov 2026", "Dec 2026", "Jan 2027", "Feb 2027", "Mar 2027"
        ]
        if clicked_x in valid_months_for_fy27:
            clicked_month = clicked_x

    if clicked_month is not None:
        df_fy27 = df_fy27[df_fy27["Month_Str"] == clicked_month].copy()

    # Map actual department names to target department names
    def map_dept(d_name):
        if not isinstance(d_name, str):
            return None
        d_clean = d_name.strip().lower()
        mapping = {
            'raw material handling system': 'RMHS Upto 5MT', 
            'sms-iv': 'SMS-4',
            'steel melting shop iv': 'SMS-4',
            'crs & i-shop': 'Central Repair Shop,ISHOP',
            'central repair shop': 'Central Repair Shop,ISHOP',
            'hr': 'Human Resources',
            'safety & f.s.': 'Safety',
            'it': 'IT & Digitalisation',
            'commercial (stores)': 'Central Stores',
            'wire rod mill i': 'Wire Rod Mill 1',
            'blast furnace i ,blast furnace ii': 'Blast Furnace 1, Blast Furnace 2',
            'blast furnace v': 'Blast Furnace V',
            'corex i & ii': 'COREX 1&2',
            'pdqc': 'Product Development & Quality Control',
            'ppc': 'Production Planning & Control(PPC)',
            'production planning & control (ppc)': 'Production Planning & Control(PPC)',
            'csd': 'Customer Service Department',
            'coke oven iii': 'Coke Ovens III',
            's1-mines office': 'S1-Mines office',
            'dri': 'Direct Reduced Iron',
            'lcp': 'Lime Calcination Plant',
            'utilities(power management)': 'Utilities',
            'bar rod mill ii': 'Bar Mill II',
        }
        for t_name in target_depts:
            if t_name.strip().lower() == d_clean:
                return t_name
        return mapping.get(d_clean, None)

    df_fy27["Target_Dept"] = df_fy27["Department"].apply(map_dept)
    selected_target_dept = map_dept(selected_dept) if selected_dept != "Overall" else None

    # Filter data based on dropdown selection
    if selected_dept != "Overall":
        if selected_target_dept is not None:
            target_df = target_df[target_df["Unnamed: 3"] == selected_target_dept]
            df_fy27 = df_fy27[df_fy27["Target_Dept"] == selected_target_dept]
        else:
            target_df = pd.DataFrame([{"Unnamed: 3": selected_dept, "OPL/POKA YOKE YearlyTarget": 0, "OPL/POKA YOKE Monthly Target": 0.0}])
            df_fy27 = df_fy27[df_fy27["Department"] == selected_dept]

    # 1. Department Wise Graph
    actual_counts = []
    target_vals = []
    dept_names = []
    
    act_map = df_fy27.groupby("Target_Dept").size().to_dict() if not df_fy27.empty else {}
    
    if selected_dept != "Overall" and selected_target_dept is None:
        actual_counts = [len(df_fy27)]
        target_vals = [0.0 if clicked_month is not None else 0]
        dept_names = [selected_dept]
    else:
        for _, r in target_df.iterrows():
            t_dept = r["Unnamed: 3"]
            dept_names.append(t_dept)
            if clicked_month is not None:
                target_vals.append(float(r["OPL/POKA YOKE Monthly Target"]))
            else:
                target_vals.append(int(r["OPL/POKA YOKE YearlyTarget"]))
            actual_counts.append(act_map.get(t_dept, 0))

    # Sort if Overall
    if selected_dept == "Overall":
        sorted_indices = sorted(range(len(target_vals)), key=lambda i: target_vals[i], reverse=True)
        dept_names = [dept_names[i] for i in sorted_indices]
        target_vals = [target_vals[i] for i in sorted_indices]
        actual_counts = [actual_counts[i] for i in sorted_indices]

    target_text = []
    for v in target_vals:
        try:
            val_float = float(v)
            if val_float.is_integer():
                target_text.append(str(int(val_float)))
            else:
                target_text.append(f"{val_float:.1f}")
        except:
            target_text.append(str(v))

    target_bar_name = "Monthly Target" if clicked_month is not None else "Yearly Target"
    actual_bar_name = f"Actual ({clicked_month})" if clicked_month is not None else "Actual OPL/Poka Yoke"
    if clicked_month is not None:
        graph_title = f"Target vs Actual OPL/Poka Yoke by Department - {clicked_month}" if selected_dept == "Overall" else f"Target vs Actual OPL/Poka Yoke - {selected_dept} ({clicked_month})"
    else:
        graph_title = "Target vs Actual OPL/Poka Yoke by Department (FY-2027)" if selected_dept == "Overall" else f"Target vs Actual OPL/Poka Yoke - {selected_dept} (FY-2027)"

    fig_dept = go.Figure(data=[
        go.Bar(
            name=actual_bar_name,
            x=dept_names,
            y=actual_counts,
            marker_color="#1a73e8",
            text=actual_counts,
            textposition="outside",
            texttemplate="%{text}",
            hovertemplate="<b>%{x}</b><br>Actual: %{y}<extra></extra>"
        ),
        go.Bar(
            name=target_bar_name,
            x=dept_names,
            y=target_vals,
            marker_color="#94a3b8",
            text=target_text,
            textposition="outside",
            texttemplate="%{text}",
            hovertemplate="<b>%{x}</b><br>Target: %{y:.0f}<extra></extra>"
        )
    ])
    
    max_val = max(max(actual_counts) if actual_counts else 0, max(target_vals) if target_vals else 0)
    y_max = max_val * 1.20 if max_val > 0 else 10

    fig_dept.update_traces(cliponaxis=False)
    
    fig_dept.update_layout(
        barmode="group",
        title=dict(
            text=graph_title,
            font=dict(size=16, family="Segoe UI", color="#0f172a")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50, b=80),
        xaxis=dict(
            tickangle=-45,
            tickfont=dict(size=10),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(203,213,225,0.6)",
            tickfont=dict(size=12),
            zeroline=False,
            range=[0, y_max]
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        uniformtext_mode="show",
        uniformtext_minsize=8
    )

    # 2. Monthly Trend Graph
    months = [
        "Apr 2026", "May 2026", "Jun 2026", "Jul 2026", "Aug 2026", "Sep 2026",
        "Oct 2026", "Nov 2026", "Dec 2026", "Jan 2027", "Feb 2027", "Mar 2027"
    ]
    df_fy27_all = df_act[df_act["FY"] == "FY-2027"].copy()
    df_fy27_all["Month_Str"] = df_fy27_all[DATE_COL].apply(
        lambda d: month_mapping.get((d.year, d.month), None) if d is not None and not pd.isna(d) else None
    )
    act_monthly_map = df_fy27_all.groupby("Month_Str").size().to_dict() if not df_fy27_all.empty else {}
    
    if selected_dept == "Overall":
        monthly_target = int(target_df["OPL/POKA YOKE Monthly Target"].sum())
    else:
        monthly_target = int(target_df["OPL/POKA YOKE Monthly Target"].iloc[0]) if not target_df.empty else 0

    target_monthly_vals = [monthly_target] * len(months)
    actual_monthly_vals = [act_monthly_map.get(m, 0) for m in months]

    fig_trend = go.Figure()
    fig_trend.add_trace(go.Scatter(
        name="Actual OPL/Poka Yoke",
        x=months,
        y=actual_monthly_vals,
        mode="lines+markers",
        line=dict(color="#1a73e8", width=3),
        marker=dict(size=8),
        hovertemplate="<b>%{x}</b><br>Actual: %{y}<extra></extra>"
    ))
    fig_trend.add_trace(go.Scatter(
        name="Monthly Target",
        x=months,
        y=target_monthly_vals,
        mode="lines+markers",
        line=dict(color="#ef4444", width=2, dash="dash"),
        marker=dict(size=6),
        hovertemplate="<b>%{x}</b><br>Target: %{y:.0f}<extra></extra>"
    ))

    fig_trend.update_layout(
        title=dict(
            text="Monthly Target vs Actual OPL/Poka Yoke Trend (FY-2027)" if selected_dept == "Overall" else f"Monthly Target vs Actual OPL/Poka Yoke Trend - {selected_dept} (FY-2027)",
            font=dict(size=16, family="Segoe UI", color="#0f172a")
        ),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50, b=50),
        xaxis=dict(
            tickfont=dict(size=12),
        ),
        yaxis=dict(
            showgrid=True,
            gridcolor="rgba(203,213,225,0.6)",
            tickfont=dict(size=12),
            zeroline=False
        ),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )

    if selected_dept == "Overall":
        graph_style = {"width": "3000px", "height": graph_height_tall}
        wrapper_style = {"overflowX": "scroll", "width": "100%"}
    else:
        graph_style = {"width": "100%", "height": graph_height_tall}
        wrapper_style = {}

    content = html.Div([
        html.H4("🎯 Target vs Actual Analysis (FY-2027)", style={"marginTop": "20px", "fontWeight": "bold", "color": "#0f172a"}),
        html.Div([
            html.Div(
                html.Div(
                    dcc.Graph(id="opl_target_dept_graph", figure=fig_dept, style=graph_style),
                    style=wrapper_style
                ),
                style=graph_card_style,
            ),
            html.Div(
                dcc.Graph(id="opl_target_trend_graph", figure=fig_trend, style={"height": graph_height_standard}),
                style=graph_card_style,
            ),
        ]),
    ])

    return content, {"display": "block"}
