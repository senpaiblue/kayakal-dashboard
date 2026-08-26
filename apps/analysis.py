import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
from app import app
dash.register_page(
    __name__,
    path="/analysis",
    name="analysis"
)

layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H2("analysis Page", className="text-center mb-3"),
                            html.H4("📊 Data Coming Soon...", className="text-center text-muted"),
                        ]
                    ),
                    class_name="mt-5 shadow"
                ),
                width=12
            )
        )
    ],
    fluid=True
)
