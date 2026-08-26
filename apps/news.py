import os
from datetime import datetime

from dash import html, dcc, Input, Output
import dash_bootstrap_components as dbc
from app import app

NEWSLETTER_FOLDER = "./assets/newsletter"

# ---------------- HELPERS ---------------- #
def get_current_quarter():
    m = datetime.today().month
    if m <= 3:
        return "first"
    elif m <= 6:
        return "second"
    elif m <= 9:
        return "third"
    else:
        return "fourth"

def get_current_year():
    return datetime.today().year

def get_pdf_path(quarter, year):
    filename = f"{quarter}{year}.pdf"
    filepath = os.path.join(NEWSLETTER_FOLDER, filename)
    return filename, filepath


# ---------------- LAYOUT ---------------- #
layout = dbc.Container([

    dbc.Card(
        dbc.CardBody([

            # ---------- HEADER ----------
            dbc.Row([
                dbc.Col(
                    html.H4("📘 Newsletter (Quarterly – FY)",
                            className="fw-bold text-primary"),
                    width="auto"
                )
            ], className="mb-3"),

            # ---------- FILTER BAR ----------
            dbc.Row([
                dbc.Col([
                    dbc.Label("Quarter", className="fw-semibold"),
                    dcc.Dropdown(
                        id="quarter-dropdown",
                        options=[
                            {"label": "First Quarter", "value": "first"},
                            {"label": "Second Quarter", "value": "second"},
                            {"label": "Third Quarter", "value": "third"},
                            {"label": "Fourth Quarter", "value": "fourth"},
                        ],
                        value=get_current_quarter(),
                        clearable=False
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("FY Year", className="fw-semibold"),
                    dcc.Dropdown(
                        id="year-dropdown",
                        options=[
                            {"label": str(y), "value": y}
                            for y in range(2020, datetime.today().year + 5)
                        ],
                        value=get_current_year(),
                        clearable=False
                    )
                ], md=3),
            ], className="mb-4"),

            # ---------- PDF VIEWER ----------
            dbc.Card(
                dbc.CardBody(
                    html.Div(
                        id="newsletter-content",
                        style={"minHeight": "75vh"}
                    )
                ),
                className="shadow-sm border"
            )

        ]),
        className="shadow-lg border rounded-4"
    )

], fluid=True, className="px-4 py-3")


# ---------------- CALLBACK ---------------- #
@app.callback(
    Output("newsletter-content", "children"),
    Input("quarter-dropdown", "value"),
    Input("year-dropdown", "value"),
)
def load_newsletter(quarter, year):

    filename, filepath = get_pdf_path(quarter, year)

    if os.path.exists(filepath):
        return html.Iframe(
            src=f"/assets/newsletter/{filename}",
            style={
                "width": "100%",
                "height": "75vh",
                "border": "1px solid #dee2e6",
                "borderRadius": "8px"
            }
        )

    return dbc.Alert(
        f"No newsletter available for {quarter.capitalize()} Quarter FY {year}",
        color="info",
        className="text-center fw-semibold"
    )
