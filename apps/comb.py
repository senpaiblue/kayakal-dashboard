import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, callback

from apps import d, self, d5s_audit_scoring, red_tag_5s

layout = dbc.Container([

    dbc.RadioItems(
        id="upload-page-switch",
        options=[
            {"label": "Summary", "value": "page3"},
            {"label": "Audit compliance", "value": "page1"},
            {"label": "Self page", "value": "page2"},
            {"label": "Red Tag", "value": "page4"},
        ],
        value="page3",
        inline=True,
        className="segmented-control mb-4",
        inputClassName="btn-check",
        labelClassName="seg-btn",
    ),


    html.Div(id="upload-page-container")

], fluid=True)
@callback(
    Output("upload-page-container", "children"),
    Input("upload-page-switch", "value")
)
def switch_upload_page(selected):
    if selected == "page3":
        return d5s_audit_scoring.layout
    if selected == "page2":
        return self.layout
    if selected == "page4":
        return red_tag_5s.layout
    return d.layout
