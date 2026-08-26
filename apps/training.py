import os
from pathlib import Path
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from app import app


import dash_bootstrap_components as dbc
from dash import html, dcc

MONTHS = [
    "january", "february", "march", "april",
    "may", "june", "july", "august",
    "september", "october", "november", "december"
]

layout = dbc.Container([

    # 🔹 Floating motivation line (same as Spotlights)
    html.Div(
        html.Div(
            [
                html.Span("🎓 Training Builds Skills — Skills Build Excellence", className="marquee-item one"),
                html.Span("📘 Learning Today, Performing Better Tomorrow", className="marquee-item two"),
            ],
            className="marquee-text"
        ),
        className="marquee-container"
    ),

    dbc.Row([

        # Year dropdown
        dbc.Col([
            dbc.Label("Select Year", className="fw-semibold"),
            dcc.Dropdown(
                id="training-year",
                clearable=False
            )
        ], md=3),

        # Month buttons
        dbc.Col([
            dbc.Label("Select Month", className="fw-semibold"),
            dbc.ButtonGroup(
                [
                    dbc.Button(
                        m.title(),
                        id=f"month-btn-{m}",
                        color="outline-primary",
                        size="sm",
                        n_clicks=0
                    )
                    for m in MONTHS
                ],
                className="flex-wrap"
            )
        ], md=9),

    ], className="mb-3"),

    # Image area
    html.Div(id="training-image-container")

], fluid=True, className="mt-3")


from dash import Input, Output, State, ctx
from datetime import datetime
from pathlib import Path

TRAINING_FOLDER = Path("./assets/training")

def get_training_files():
    data = {}
    for f in TRAINING_FOLDER.glob("*.*"):
        name = f.stem.lower()
        for m in MONTHS:
            if name.startswith(m):
                try:
                    year = int(name.replace(m, ""))
                    data.setdefault(year, {})[m] = f.name
                except ValueError:
                    pass
    return data


@app.callback(
    Output("training-year", "options"),
    Output("training-year", "value"),
    Output("training-image-container", "children"),
    [Input("training-year", "value")] +
    [Input(f"month-btn-{m}", "n_clicks") for m in MONTHS],
)
def update_training(year, *month_clicks):

    data = get_training_files()
    now = datetime.now()

    years = sorted(data.keys(), reverse=True)
    year = year or (now.year if now.year in years else years[0])

    # Detect clicked month
    triggered = ctx.triggered_id
    if triggered and triggered.startswith("month-btn-"):
        month = triggered.replace("month-btn-", "")
    else:
        month = now.strftime("%B").lower()

    # Build image
    if year in data and month in data[year]:
        img = html.Img(
            src=f"/assets/training/{data[year][month]}",
            style={
                "width": "100%",
                "maxHeight": "80vh",
                "objectFit": "contain",
                "borderRadius": "8px",
                "boxShadow": "0 4px 12px rgba(0,0,0,0.15)"
            }
        )
    else:
        img = html.Div(
            f"No training material for {month.title()} {year}",
            className="text-muted fw-semibold mt-5"
        )

    return (
        [{"label": y, "value": y} for y in years],
        year,
        img
    )
