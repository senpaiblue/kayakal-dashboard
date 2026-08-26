import dash
from app import app
import pandas as pd
import datetime as dt
from pathlib import Path
from dash import Dash, html, dcc, Input, Output, callback_context
from dash import dash_table
import plotly.express as px
from apps import analysis,dashboard,reports,settings,summary,home
import dash_bootstrap_components as dbc
# ---------------- CONFIG ----------------
CSV_PATH = ".\Data\KZ_REPORT.csv"   # <-- set your CSV path
DATE_COL = "TransactionDate"
# ----------------------------------------

# Load CSV (robust encoding)
if not Path(CSV_PATH).exists():
    raise FileNotFoundError(f"CSV not found at {CSV_PATH}")

def read_csv_safely(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to read CSV with any known encoding. Convert file to UTF-8 or CP1252.")

df = read_csv_safely(CSV_PATH)
df.columns = df.columns.str.strip()    #the name of the god have been for 


# Ensure date column exists and parse it
if DATE_COL not in df.columns:
    raise KeyError(f"CSV must contain '{DATE_COL}' column")

df[DATE_COL] = pd.to_datetime(df[DATE_COL].str.strip(), dayfirst=True, errors="coerce")

# Ensure grouping columns exist
for col in ["KaizenID", "TICName", "Department",
            "ImplementedByFirstPerson", "Emp1Code", "Emp1Grade", "KaizenImpact", "KaizenCategory"]:
    if col not in df.columns:
        df[col] = pd.NA

# Fill grouping labels (so charts don't break on NaN)
df["KaizenID"] = df["KaizenID"].fillna("Unknown").astype(str)
df["TICName"] = df["TICName"].fillna("Unknown").astype(str)
df["Department"] = df["Department"].fillna("Unknown").astype(str)

# Default last-30-days window (based on data max date)
today = dt.date.today()
default_end = today
default_start = today - dt.timedelta(days=29)


# Dash app
app = Dash(__name__)
server = app.server

# Shared styles so charts remain the same size
container_style = {
    "width": "24%",
    "display": "inline-block",
    "verticalAlign": "top",
    "border": "1px solid #d0d7de",
    "borderRadius": "8px",
    "padding": "8px",
    "boxSizing": "border-box",
    "backgroundColor": "#fff",
    "height": "380px",
    "overflow": "hidden"
}

from dash import Dash, html
import dash
from dash import page_container, page_registry


button_style = {
    'color': '#fff',
    'zIndex': 1000  # Ensure buttons are in front of background
}
app.layout = html.Div([
      dcc.Location(id="_pages_location"),
      dash.page_container,


    # Header
    html.Div([
        html.Img(src="/assets/logo.jpg", className="logo"),
        dbc.Col([
            dbc.Button('Home', href='/', color='link', outline=True, style=button_style),
            dbc.Button('Analysis', href='/Analysis', target='_blank', color='link', outline=True, style=button_style),
            dbc.Button('Reports', href='/Reports', color='link', outline=True, style=button_style),
            dbc.Button('Settings', href='/Settings', color='link', outline=True, style=button_style),
            dbc.Button('Summary', href='/Summary', color='link', outline=True, style=button_style),
            
        ], md=8,
            align='end',
            class_name='text-end',
            style={
                'border-radius': '15px',
                'padding-top': '0',
                'border-color': '#0a58ca',
                'border-style': 'solid',
                'background': '#0a58ca',
                'zIndex': 1000  # Ensure buttons are in front of background
            }
        ),
    ], className="top-nav"),

    dbc.Row([
        dbc.Col([
            dcc.Location(id='page_navi'),
            dcc.Loading(children=[html.Div(id='main_output', style={'margin-top': '20px'})],
                        type='graph', color='red', fullscreen=True)
        ], width=12)
    ],
        # class_name = 'navbar-content'
    ),
])


@app.callback(Output('main_output', 'children'), Input('page_navi', 'pathname'))
def main_content_loader(pathname):
        if pathname == '/Reports':
            return reports.layout
        elif pathname == '/Analysis':
            return analysis.layout
        elif pathname == '/':
            return home.layout
        elif pathname == '/Dashboard':
            return dashboard.layout
        elif pathname == '/Summary':
            return summary.layout
        elif pathname == '/Settings':
            return settings.layout

# ----------------- Run server -----------------
if __name__ == "__main__":
    # Dash 3.x: app.run()
    app.run(debug=True, port=8050)


