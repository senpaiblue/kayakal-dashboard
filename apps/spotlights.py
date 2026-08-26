import os
from pathlib import Path
from datetime import datetime

import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
from app import app
from flask import send_from_directory

# ---------------- CONFIG ---------------- #
PDF_FOLDER = Path("./assets/highlight")

PDF_FOLDER.mkdir(parents=True, exist_ok=True)

# ---------------- HELPERS ---------------- #
from datetime import datetime
from pathlib import Path

PDF_FOLDER = Path("./assets/highlight")

def get_all_pdfs():
    pdfs = {}
    for f in PDF_FOLDER.glob("*.pdf"):
        try:
            d = datetime.strptime(f.stem, "%d-%m-%Y").date()
            pdfs[d] = f.name
        except ValueError:
            pass
    return pdfs

def get_latest_pdf(pdf_map):
    latest_date = max(pdf_map.keys())
    return latest_date, pdf_map[latest_date]

# ---------------- LAYOUT ---------------- #
layout = dbc.Container([

    # 🔹 Floating text
    html.Div(
    html.Div(
        [
            html.Span(
                "✨🌱 Continuous Improvement is Not an Event — It’s a Culture 🌱",
                className="marquee-item one"
            ),
            html.Span(
                "🌿 Kaizen Spotlight: Small Improvements Today, Big Results Tomorrow",
                className="marquee-item two"
            ),
            html.Span(
                "📈 Measure. Analyze. Improve. Sustain.",
                className="marquee-item three"
            ),
            html.Span(
                "👏 Celebrating Teams That Drive Quality Forward",
                className="marquee-item four"
            ),
        ],
        className="marquee-text"
    ),
    className="marquee-container"
),

    dbc.Card([
        dbc.CardHeader(
            html.H4("📌 Highlights – PDF Viewer", className="mb-0")
        ),
        dbc.CardBody([

            dbc.Row([
                dbc.Col([
                    dbc.Label("Select Available Date", className="fw-semibold"),
                    dcc.Dropdown(
                        id="highlight-date",
                        placeholder="Select latest available date",
                        clearable=False
                    )
                ], md=4),
            ], className="mb-3"),

            html.Iframe(
                id="pdf_viewer",
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



# ---------------- CALLBACK ---------------- #
from flask import send_from_directory

@app.server.route("/highlightpdf/<path:filename>")
def serve_highlight_pdf(filename):
    return send_from_directory(PDF_FOLDER, filename)


@app.callback(
    Output("pdf_viewer", "src"),
    Output("highlight-date", "options"),
    Output("highlight-date", "value"),
    Input("highlight-date", "value")
)
def update_highlight(selected_date):

    pdf_map = get_all_pdfs()

    if not pdf_map:
        return "", [], None

    # Sort dates DESCENDING
    sorted_dates = sorted(pdf_map.keys(), reverse=True)

    options = [
        {"label": d.strftime("%d-%m-%Y"), "value": d.strftime("%d-%m-%Y")}
        for d in sorted_dates
    ]

    latest_date = sorted_dates[0]
    latest_file = pdf_map[latest_date]

    if selected_date:
        sel_date = datetime.strptime(selected_date, "%d-%m-%Y").date()
        if sel_date in pdf_map:
            return (
                f"/highlightpdf/{pdf_map[sel_date]}",
                options,
                selected_date
            )

    # Default → latest PDF
    return (
        f"/highlightpdf/{latest_file}",
        options,
        latest_date.strftime("%d-%m-%Y")
    )
