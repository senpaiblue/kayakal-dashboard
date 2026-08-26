# main.py
import pandas as pd
import datetime as dt
from pathlib import Path

from dash import Dash, html, dcc, Input, Output, callback_context
import dash_table
import plotly.express as px

# ---------------- CONFIG ----------------
CSV_PATH = ".\Data\KZ_REPORT.csv"   # <-- set your CSV path
DATE_COL = "TransactionDate"
# ----------------------------------------

# Load CSV (robust encoding)
if not Path(CSV_PATH).exists():
    raise FileNotFoundError(f"CSV not found at {CSV_PATH}")

df = pd.read_csv(CSV_PATH, encoding="cp1252", dtype=str)
df.columns = df.columns.str.strip()

# Ensure date column exists and parse it
if DATE_COL not in df.columns:
    raise KeyError(f"CSV must contain '{DATE_COL}' column")

df[DATE_COL] = pd.to_datetime(df[DATE_COL].str.strip(), dayfirst=True, errors="coerce")

# Ensure grouping columns exist
for col in ["KaizenID", "TICName", "Department",
            "ImplementedByFirstPerson", "Emp1Code", "Emp1Grade", "KaizenImpact", "KaizenCategory"]:
    if col not in df.columns:
        df[col] = pd.NA

# Fill grouping labels (so charts don't break on NaN)
df["KaizenID"] = df["KaizenID"].fillna("Unknown").astype(str)
df["TICName"] = df["TICName"].fillna("Unknown").astype(str)
df["Department"] = df["Department"].fillna("Unknown").astype(str)

# Default last-30-days window (based on data max date)
max_date = df[DATE_COL].max().date() if not df[DATE_COL].isna().all() else dt.date.today()
default_end = max_date
default_start = max_date - dt.timedelta(days=29)

# Dash app
app = Dash(__name__)
server = app.server

# Shared styles so charts remain the same size
container_style = {
    "width": "32%",
    "display": "inline-block",
    "verticalAlign": "top",
    "border": "1px solid #d0d7de",
    "borderRadius": "8px",
    "padding": "8px",
    "boxSizing": "border-box",
    "backgroundColor": "#fff",
    "height": "380px",
    "overflow": "hidden"
}

app.layout = html.Div([
    html.H2("Kaizen Drilldown Dashboard", style={"textAlign": "center"}),

    # Date picker
    html.Div([
        html.Label("Select Date Range:", style={"fontWeight": "600", "marginRight": "12px"}),
        dcc.DatePickerRange(
            id="date_range",
            min_date_allowed=df[DATE_COL].min().date() if not df[DATE_COL].isna().all() else default_start,
            max_date_allowed=df[DATE_COL].max().date() if not df[DATE_COL].isna().all() else default_end,
            start_date=default_start,
            end_date=default_end,
            display_format="DD-MM-YYYY"
        )
    ], style={"padding": "10px", "border": "1px solid #d0d7de", "borderRadius": "8px", "display": "inline-block", "marginBottom": "12px"}),

    html.Div(id="summary-text", style={"marginTop": "8px", "marginBottom": "12px"}),

    # PIE row
    html.Div([
        html.Div(dcc.Graph(id="pie_status", clear_on_unhover=True), style=container_style),
        html.Div(dcc.Graph(id="pie_tic", clear_on_unhover=True),    style={**container_style, "marginLeft": "1%"}),
        html.Div(dcc.Graph(id="pie_dept", clear_on_unhover=True),   style={**container_style, "marginLeft": "1%"}),
    ], style={"width": "100%", "textAlign": "center", "marginBottom": "12px"}),

    # BAR row
    html.Div([
        html.Div(dcc.Graph(id="bar_status", clear_on_unhover=True), style=container_style),
        html.Div(dcc.Graph(id="bar_tic", clear_on_unhover=True),    style={**container_style, "marginLeft": "1%"}),
        html.Div(dcc.Graph(id="bar_dept", clear_on_unhover=True),   style={**container_style, "marginLeft": "1%"}),
    ], style={"width": "100%", "textAlign": "center", "marginBottom": "12px"}),

    # Table container
    html.Div(id="details_table", style={"marginTop": "12px"}),

], style={"padding": "20px", "fontFamily": "Arial"})

# ----------------- Callback 1: PIE charts (pie clicks affect only downstream pies) -----------------
@app.callback(
    Output("pie_status", "figure"),
    Output("pie_tic", "figure"),
    Output("pie_dept", "figure"),
    Output("summary-text", "children"),

    Input("date_range", "start_date"),
    Input("date_range", "end_date"),
    Input("pie_status", "clickData"),
    Input("pie_tic", "clickData"),
)
def update_pies(start_date, end_date, pie1_click, pie2_click):
    # Base date filter (applies to all pie calculations)
    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]
    summary = f"Showing {len(base)} rows from {s.strftime('%d-%m-%Y')} to {e.strftime('%d-%m-%Y')}."

    # PIE1: always from base (so clicking won't make it 100% unless real)
    pie1 = px.pie(base, names="KaizenID", title="By Kaizen Status", hole=0.35)
    pie1.update_traces(textinfo="percent+label")

    # PIE2: filtered by pie1 selection (if any) — note: pie1_click only controls pie2/3
    sel_status = None
    if pie1_click and "points" in pie1_click:
        sel_status = pie1_click["points"][0].get("label") or pie1_click["points"][0].get("x")

    pie2_df = base if not sel_status else base[base["KaizenID"] == sel_status]
    pie2 = px.pie(pie2_df, names="TICName", title=f"By TIC Name{(' • ' + sel_status) if sel_status else ''}", hole=0.35)
    pie2.update_traces(textinfo="percent+label")

    # PIE3: filtered by pie1 and pie2 selections
    sel_tic = None
    if pie2_click and "points" in pie2_click:
        sel_tic = pie2_click["points"][0].get("label") or pie2_click["points"][0].get("x")

    pie3_df = pie2_df if not sel_tic else pie2_df[pie2_df["TICName"] == sel_tic]
    pie3 = px.pie(pie3_df, names="Department", title=f"By Department{(' • ' + (sel_tic or sel_status)) if (sel_tic or sel_status) else ''}", hole=0.35)
    pie3.update_traces(textinfo="percent+label")

    return pie1, pie2, pie3, summary

# ----------------- Callback 2: BAR charts (bar clicks affect only downstream bars) -----------------
@app.callback(
    Output("bar_status", "figure"),
    Output("bar_tic", "figure"),
    Output("bar_dept", "figure"),

    Input("date_range", "start_date"),
    Input("date_range", "end_date"),
    Input("bar_status", "clickData"),
    Input("bar_tic", "clickData"),
)
def update_bars(start_date, end_date, bar1_click, bar2_click):
    # Base date filter
    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]

    # BAR1: always base
    bar1_df = base.groupby("KaizenID").size().reset_index(name="count").sort_values("count", ascending=False)
    bar1 = px.bar(bar1_df, x="KaizenID", y="count", text="count", title="Status Count")
    bar1.update_traces(textposition="outside")
    bar1.update_layout(xaxis_tickangle=-45)

    # BAR2: filtered by bar1 selection if provided
    sel_status = None
    if bar1_click and "points" in bar1_click:
        sel_status = bar1_click["points"][0].get("label") or bar1_click["points"][0].get("x")

    bar2_df = base if not sel_status else base[base["KaizenID"] == sel_status]
    bar2_group = bar2_df.groupby("TICName").size().reset_index(name="count").sort_values("count", ascending=False)
    bar2 = px.bar(bar2_group, x="TICName", y="count", text="count", title=f"TIC Name Count{(' • ' + sel_status) if sel_status else ''}")
    bar2.update_traces(textposition="outside")
    bar2.update_layout(xaxis_tickangle=-45)

    # BAR3: filtered by bar1 and bar2 selection
    sel_tic = None
    if bar2_click and "points" in bar2_click:
        sel_tic = bar2_click["points"][0].get("label") or bar2_click["points"][0].get("x")

    bar3_df = bar2_df if not sel_tic else bar2_df[bar2_df["TICName"] == sel_tic]
    bar3_group = bar3_df.groupby("Department").size().reset_index(name="count").sort_values("count", ascending=False)
    bar3 = px.bar(bar3_group, x="Department", y="count", text="count", title=f"Department Count{(' • ' + (sel_tic or sel_status)) if (sel_tic or sel_status) else ''}")
    bar3.update_traces(textposition="outside")
    bar3.update_layout(xaxis_tickangle=-45)

    return bar1, bar2, bar3

# ----------------- Callback 3: Table (triggered only by bar_dept click) -----------------
@app.callback(
    Output("details_table", "children"),
    Input("bar_dept", "clickData"),
    Input("date_range", "start_date"),
    Input("date_range", "end_date"),
    Input("bar_status", "clickData"),
    Input("bar_tic", "clickData"),
)
def update_table(bar3_click, start_date, end_date, bar1_click, bar2_click):
    # If no bar3 click, don't show table
    if not bar3_click or "points" not in bar3_click:
        return ""

    try:
        s = pd.to_datetime(start_date).date()
        e = pd.to_datetime(end_date).date()
    except Exception:
        s, e = default_start, default_end

    base = df[(df[DATE_COL].dt.date >= s) & (df[DATE_COL].dt.date <= e)]

    # Respect bar1 and bar2 context if clicked
    if bar1_click and "points" in bar1_click:
        v = bar1_click["points"][0].get("label") or bar1_click["points"][0].get("x")
        base = base[base["KaizenID"] == v]

    if bar2_click and "points" in bar2_click:
        v = bar2_click["points"][0].get("label") or bar2_click["points"][0].get("x")
        base = base[base["TICName"] == v]

    # Final dept clicked
    dept_val = bar3_click["points"][0].get("label") or bar3_click["points"][0].get("x")
    base = base[base["Department"] == dept_val]

    if base.empty:
        return html.Div(f"No rows for Department '{dept_val}' in the selected date range.", style={"padding": "8px"})

    # Prepare table with date column included
    table_df = base[[
        DATE_COL,
        "ImplementedByFirstPerson",
        "Emp1Code",
        "Emp1Grade",
        "KaizenImpact",
        "KaizenCategory"
    ]].rename(columns={
        DATE_COL: "Date",
        "ImplementedByFirstPerson": "Name of Emp",
        "Emp1Code": "Emp Code",
        "Emp1Grade": "Grade",
        "KaizenImpact": "Kaizen Impact",
        "KaizenCategory": "Kaizen Category"
    }).fillna("")

    # Format Date column nicely
    try:
        table_df["Date"] = pd.to_datetime(table_df["Date"]).dt.strftime("%d-%m-%Y")
    except Exception:
        pass

    # Use Dash DataTable for nice display
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

# ----------------- Run server -----------------
if __name__ == "__main__":
    # Dash 3.x: app.run()
    app.run(debug=True,host='0.0.0.0', port=1000)
