import re
from pathlib import Path
from datetime import datetime, date

import pandas as pd
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import plotly.graph_objects as go
from server import app

# ==========================================================
# STARTUP DEBUG
# ==========================================================
print("\n🔥 APP FILE LOADED 🔥", flush=True)
print("DEBUG: __file__ =", __file__, flush=True)
print("DEBUG: CWD =", Path.cwd(), flush=True)

# ==========================================================
# LOG FILE PATH
# ==========================================================
BASE_DIR = Path(__file__).resolve().parent.parent
LOG_FILE = BASE_DIR / "logs.txt"

print("DEBUG: BASE_DIR =", BASE_DIR, flush=True)
print("DEBUG: LOG_FILE =", LOG_FILE, flush=True)
print("DEBUG: LOG_FILE exists =", LOG_FILE.exists(), flush=True)

# ==========================================================
# LOG PARSER REGEX
# ==========================================================
LOG_PATTERN = re.compile(
    r'(?P<ip>\d+\.\d+\.\d+\.\d+).*?\[(?P<dt>\d{2}/[A-Za-z]{3}/\d{4} \d{2}:\d{2}:\d{2})\]'
)

# ==========================================================
# READ LOGS (CACHED)
# ==========================================================
_logs_cache = {
    "df": None,
    "mtime": 0.0
}

def read_logs():
    if not LOG_FILE.exists():
        return pd.DataFrame()

    try:
        mtime = LOG_FILE.stat().st_mtime
        if _logs_cache["df"] is not None and _logs_cache["mtime"] == mtime:
            return _logs_cache["df"].copy()

        rows = []
        with LOG_FILE.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                m = LOG_PATTERN.search(line)
                if not m:
                    continue

                dt = datetime.strptime(
                    m.group("dt"),
                    "%d/%b/%Y %H:%M:%S"
                )

                rows.append({
                    "ip": m.group("ip"),
                    "datetime": dt,
                    "date": dt.date(),
                    "month_num": dt.month
                })

        df = pd.DataFrame(rows)
        _logs_cache["df"] = df
        _logs_cache["mtime"] = mtime
        return df.copy()

    except Exception as e:
        print("❌ FILE READ ERROR:", e, flush=True)
        return pd.DataFrame()

# ==========================================================
# DASH LAYOUT
# ==========================================================
layout = dbc.Container(
    [
        # 🔢 KPI CARD
        dbc.Row(
            [
                dbc.Col(
                    dbc.Card(
                        dbc.CardBody(
                            [
                                html.H6("👥 Total Users Today", className="text-muted"),
                                html.H2(id="total-users-today", className="fw-bold mb-0"),
                                html.Small(id="today-date", className="text-muted")
                            ]
                        ),
                        className="shadow-sm"
                    ),
                    md=4
                )
            ],
            className="mb-3"
        ),

        dbc.Card(
            [
                dbc.CardHeader(
                    html.H4("📊 Application Visitor Analytics", className="mb-0")
                ),
                dbc.CardBody(
                    [
                        dcc.Interval(
                            id="log-refresh",
                            interval=60 * 1000,
                            n_intervals=0
                        ),

                        dcc.Graph(
                            id="daily-visitors-graph",
                            style={"height": "420px"}
                        ),

                        html.Hr(),

                        dbc.Row(
                            [
                                dbc.Col(
                                    dcc.Graph(
                                        id="yearly-visitors-graph",
                                        style={"height": "350px"}
                                    ),
                                    md=6
                                ),

                                dbc.Col(
                                    [
                                        html.H6(
                                            "Visitors on Selected Date",
                                            className="fw-bold"
                                        ),
                                        dbc.Table(
                                            id="visitor-table",
                                            bordered=True,
                                            striped=True,
                                            hover=True,
                                            size="sm"
                                        )
                                    ],
                                    md=6
                                )
                            ]
                        )
                    ]
                )
            ],
            className="shadow-sm"
        )
    ],
    fluid=True,
    className="mt-3"
)

# ==========================================================
# UPDATE KPI + GRAPHS
# ==========================================================
@app.callback(
    Output("total-users-today", "children"),
    Output("today-date", "children"),
    Output("daily-visitors-graph", "figure"),
    Output("yearly-visitors-graph", "figure"),
    Input("log-refresh", "n_intervals")
)
def update_dashboard(n):
    df = read_logs()
    today = date.today()
    today_label = today.strftime("%d %b %Y")

    if df.empty:
        return "0", f"Today: {today_label}", go.Figure(), go.Figure()

    # KPI: UNIQUE USERS TODAY
    users_today = df[df["date"] == today]["ip"].nunique()

    # DAILY GRAPH
    daily = (
        df.groupby("date")["ip"]
        .nunique()
        .reset_index(name="users")
        .sort_values("date")
        .tail(30)
    )

    # MONTHLY GRAPH
    yearly = (
        df.groupby("month_num")["ip"]
        .nunique()
        .reset_index(name="users")
        .sort_values("month_num")
    )
    yearly["month"] = yearly["month_num"].apply(
        lambda x: datetime(1900, x, 1).strftime("%b")
    )

    fig_daily = go.Figure(
        go.Scatter(
            x=daily["date"],
            y=daily["users"],
            mode="lines+markers+text",
            text=daily["users"],
            textposition="top center",
            line=dict(width=3),
            marker=dict(
                size=10,
                color="#1f77b4",
                line=dict(width=2, color="white")
            )
        )
    )

    fig_year = go.Figure(
        go.Scatter(
            x=yearly["month"],
            y=yearly["users"],
            mode="lines+markers+text",
            text=yearly["users"],
            textposition="top center",
            line=dict(width=3),
            marker=dict(
                size=10,
                color="#2ca02c",
                line=dict(width=2, color="white")
            )
        )
    )

    for fig, xlabel in [(fig_daily, "Date"), (fig_year, "Month")]:
        fig.update_layout(
            template="plotly_white",
            hovermode="x unified",
            transition=dict(duration=600, easing="cubic-in-out"),
            xaxis_title=xlabel,
            yaxis_title="Unique Users",
            margin=dict(l=40, r=20, t=40, b=40)
        )

    return str(users_today), f"Today: {today_label}", fig_daily, fig_year

# ==========================================================
# UPDATE TABLE (ONE USER = ONE ROW)
# ==========================================================
@app.callback(
    Output("visitor-table", "children"),
    Input("daily-visitors-graph", "clickData")
)
def update_table(clickData):
    if not clickData:
        return html.Tbody([])

    clicked_date = pd.to_datetime(
        clickData["points"][0]["x"]
    ).date()

    df = read_logs()
    day_df = df[df["date"] == clicked_date]

    if day_df.empty:
        return html.Tbody([])

    summary = (
        day_df
        .groupby("ip")
        .agg(
            visits=("ip", "count"),
            first_seen=("datetime", "min"),
            last_seen=("datetime", "max")
        )
        .reset_index()
        .sort_values("visits", ascending=False)
    )

    rows = [
        html.Tr([
            html.Td(r["ip"]),
            html.Td(r["visits"]),
            html.Td(r["first_seen"].strftime("%H:%M:%S")),
            html.Td(r["last_seen"].strftime("%H:%M:%S")),
        ])
        for _, r in summary.iterrows()
    ]

    return [
        html.Thead(
            html.Tr([
                html.Th("IP"),
                html.Th("Visits"),
                html.Th("First Seen"),
                html.Th("Last Seen"),
            ])
        ),
        html.Tbody(rows)
    ]
