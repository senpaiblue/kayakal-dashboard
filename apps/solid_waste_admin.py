import dash
from dash import html
import dash_bootstrap_components as dbc

# Page registration
dash.register_page(__name__, path="/solid-waste-admin")

# Simple placeholder layout redirecting to the main page
layout = dbc.Container([
    dbc.Card([
        dbc.CardBody([
            html.H4("Solid Waste Admin Page", className="text-center fw-bold mb-3", style={"color": "#1e3d59"}),
            html.P(
                "This administrative page is no longer active as the solid waste management approval workflow has been simplified into a single comprehensive dashboard.",
                className="text-muted text-center"
            ),
            html.Div(
                dbc.Button("Go to Solid Waste Dashboard", href="/solid-waste-management", color="primary", className="fw-bold shadow-sm px-4 py-2", style={"borderRadius": "10px"}),
                className="text-center mt-4"
            )
        ], className="p-4")
    ], className="border-0 shadow-sm mx-auto my-5", style={"borderRadius": "16px", "maxWidth": "500px"})
], fluid=True, style={"backgroundColor": "#f4f7fc", "minHeight": "100vh", "paddingTop": "100px"})
