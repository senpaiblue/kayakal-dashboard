import os
from pathlib import Path
import pandas as pd
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from app import app
from flask import send_from_directory
PLAN_FILE = Path("./assets/NUGGETS/plan.csv")
NUGGETS_FOLDER = Path("./assets/NUGGETS")

NUGGETS_FOLDER.mkdir(parents=True, exist_ok=True)

def read_plan():
    return pd.read_csv(PLAN_FILE)


def get_topics():
    df = read_plan()
    return [col for col in df.columns if not col.startswith("Unnamed")]


def get_nuggets_by_topic(topic):
    df = read_plan()
    nuggets = (
        df[topic]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )
    return nuggets


def get_latest_nugget():
    """
    Latest nugget = last non-empty value
    checking columns from right to left
    """
    df = read_plan()

    for col in reversed(df.columns):
        series = df[col].dropna()
        if not series.empty:
            return col, series.iloc[-1]

    return None, None

from flask import send_from_directory
from app import app

@app.server.route("/nuggets/<path:filename>")
def serve_nugget_image(filename):
    return send_from_directory(NUGGETS_FOLDER, filename)

layout = dbc.Container([

    dbc.Card([

        dbc.CardHeader(
            html.H4("📘 Quality Nuggets Library", className="mb-0")
        ),

        dbc.CardBody([

            dbc.Row([

                dbc.Col([
                    dbc.Label("Select Topic", className="fw-semibold"),
                    dcc.Dropdown(
                        id="topic-select",
                        placeholder="Select Topic",
                        clearable=False
                    )
                ], md=4),

                dbc.Col([
                    dbc.Label("Select Nugget", className="fw-semibold"),
                    dcc.Dropdown(
                        id="nugget-select",
                        placeholder="Select Nugget",
                        clearable=False
                    )
                ], md=4),

            ], className="mb-3"),

            html.H5(
                id="nugget-title",
                className="text-center text-primary fw-bold mb-1"
            ),

            html.P(
                id="nugget-date",
                className="text-center text-muted mb-3"
            ),

            html.Img(
                id="nugget-image",
                style={
                    "maxWidth": "100%",
                    "maxHeight": "80vh",
                    "display": "block",
                    "margin": "auto",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "8px"
                }
            )

        ])

    ], className="shadow-sm")

], fluid=True, className="mt-3")
from dash import Input, Output

@app.callback(
    Output("topic-select", "options"),
    Output("topic-select", "value"),
    Input("topic-select", "id")
)
def load_topics(_):
    topics = get_topics()
    options = [{"label": t, "value": t} for t in topics]

    return options, topics[0] if topics else None

@app.callback(
    Output("nugget-select", "options"),
    Output("nugget-select", "value"),
    Input("topic-select", "value")
)
def load_nuggets(topic):
    if not topic:
        return [], None

    nuggets = get_nuggets_by_topic(topic)
    options = [{"label": n, "value": n} for n in nuggets]

    return options, nuggets[-1] if nuggets else None

@app.callback(
    Output("nugget-image", "src"),
    Output("nugget-title", "children"),
    Input("nugget-select", "value")
)
def show_nugget(nugget):

    if not nugget:
        topic, nugget = get_latest_nugget()
        if not nugget:
            return None, ""

    for ext in [".png", ".jpg", ".jpeg"]:
        file = f"{nugget}{ext}"
        if (NUGGETS_FOLDER / file).exists():
            return f"/nuggets/{file}", nugget

    return None, nugget
