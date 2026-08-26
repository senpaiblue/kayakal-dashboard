import os
from pathlib import Path
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from app import app
from flask import send_from_directory

# ---------------- CONFIG ---------------- #
PDF_FOLDER = Path("./Data/magazine")
PDF_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------- HELPERS ---------------- #
def get_all_magazines():
    files = []
    for f in PDF_FOLDER.glob("*.pdf"):
        files.append({
            "title": f.stem,
            "file": f.name,
            "mtime": f.stat().st_mtime
        })

    # Sort by latest modified first
    files.sort(key=lambda x: x["mtime"], reverse=True)
    return files


# ---------------- LAYOUT ---------------- #
layout = dbc.Container([

    # 🔹 Floating marquee (Magazine topics)
    html.Div(
        html.Div(
            [
                html.Span(
                    "📘 TQM Magazine — Stories of Continuous Improvement",
                    className="marquee-item one"
                ),
                html.Span(
                    "🏭 From Shopfloor to Strategy — Real Kaizen Journeys",
                    className="marquee-item two"
                ),
                html.Span(
                    "📊 Data-Driven Quality | People-Driven Excellence",
                    className="marquee-item three"
                ),
                html.Span(
                    "👏 Celebrating Innovation, Safety & Productivity",
                    className="marquee-item four"
                ),
            ],
            className="marquee-text"
        ),
        className="marquee-container"
    ),

    dbc.Card([

        dbc.CardHeader(
            html.H4("📚 TQM Magazine Library", className="mb-0")
        ),

        dbc.CardBody([

            dbc.Row([
                dbc.Col([
                    dbc.Label("Select Magazine", className="fw-semibold"),
                    dcc.Dropdown(
                        id="magazine-select",
                        clearable=False,
                        placeholder="Select latest magazine"
                    )
                ], md=4),
            ], className="mb-3"),

            html.H5(
                id="magazine-title",
                className="text-center text-primary fw-bold mb-2"
            ),

            html.Iframe(
                id="magazine-viewer",
                style={
                    "width": "100%",
                    "height": "85vh",
                    "border": "1px solid #dee2e6",
                    "borderRadius": "8px"
                }
            )

        ])

    ], className="shadow-sm")

], fluid=True, className="mt-3")
@app.server.route("/magazinepdf/<path:filename>")
def serve_magazine_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)


@app.callback(
    Output("magazine-viewer", "src"),
    Output("magazine-select", "options"),
    Output("magazine-select", "value"),
    Output("magazine-title", "children"),
    Input("magazine-select", "value")
)
def update_magazine(selected_file):

    magazines = get_all_magazines()

    if not magazines:
        return "", [], None, ""

    options = [
        {"label": m["title"], "value": m["file"]}
        for m in magazines
    ]

    latest = magazines[0]

    # If user selected something
    if selected_file:
        for m in magazines:
            if m["file"] == selected_file:
                return (
                    f"/magazinepdf/{m['file']}",
                    options,
                    selected_file,
                    m["title"]
                )

    # Default → latest magazine
    return (
        f"/magazinepdf/{latest['file']}",
        options,
        latest["file"],
        latest["title"]
    )
