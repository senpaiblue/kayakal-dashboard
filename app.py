# importing dash Modules
import dash
import dash_bootstrap_components as dbc

app = dash.Dash(
    __name__,
    external_stylesheets=[
        dbc.themes.BOOTSTRAP,  
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.css"
    ],
)

server = app.server  # the Flask app
app.title = 'TQM Dashboard'
app.config.suppress_callback_exceptions = True
