from dash import Dash
import dash_bootstrap_components as dbc

app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    title="Admin Panel TQM-vjnr Dashboard",
    external_stylesheets=[dbc.themes.BOOTSTRAP]
)

server = app.server

external_stylesheets = [
    dbc.themes.BOOTSTRAP,
    "https://use.fontawesome.com/releases/v6.4.0/css/all.css",]