import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(
    __name__,
    path="/summary",
    name="summary"
)

layout = dbc.Container(
    [
        dbc.Row(
            dbc.Col(
                dbc.Card(
                    dbc.CardBody(
                        [
                            html.H2("summary Page", className="text-center mb-3"),
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
