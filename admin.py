import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import dash

from apps import sentry, b, em_admin
from app import app
from app import server

JSW_Group_logo = "https://upload.wikimedia.org/wikipedia/en/3/3c/JSW_Group_logo.svg"

# Styling for the buttons
button_style = {
    'color': '#fff',
    'zIndex': 1000  # Ensure buttons are in front of background
}

app.layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.A(
                html.Div([
                    html.Img(src=JSW_Group_logo, height="60px", style={'margin': "10px 10px 0 0", 'display': 'inline', 'vertical-align': 'bottom', 'zIndex': 1000}),
                    html.H1(
                        "VJNR Coke Ovens",
                        style={"margin-bottom": "0px", 'textAlign': 'center', 'color': '#FF1700', 'vertical-align': 'super', 'fontSize': '2rem', 'display': 'inline'},
                    )
                ], style={'padding': '0'}
                ), href='/', style={"textDecoration": "none"},
            )
        ], style={'backgroundColor': '#f8F8FF', 'zIndex': 1000}, md=4),  # Ensure logo is in front of background
        dbc.Col([
            dbc.Button('5S Image Upload', href='/sentry', color='link', outline=True, style=button_style),
            dbc.Button('Highlights', href='/b', target='_blank', color='link', outline=True, style=button_style),
            dbc.Button('Emission Admin', href='/em-admin', color='link', outline=True, style=button_style),
            dbc.Button('Newsletter', href='/dashboard', color='link', outline=True, style=button_style),
            dbc.Button('Events', href='/signin', color='link', outline=True, style=button_style),
            dbc.Button('Tranings', href='/signin2', color='link', outline=True, style=button_style),
            dbc.Button('Spotlights', href='/', color='link', outline=True, style=button_style)
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

    ], justify='between',
    ),
    dbc.Row([
        dbc.Col([
            dcc.Location(id='page_navi'),
            dcc.Loading(children=[html.Div(id='main_output', style={'margin-top': '20px'})],
                        type='graph', color='red', fullscreen=True)

        ], width=12)
    ],
        # class_name = 'navbar-content'
    )
], fluid=True)


@app.callback(Output('main_output', 'children'), Input('page_navi', 'pathname'))
def main_content_loader(pathname):
    if pathname == '/':
        return b.layout
    elif pathname == '/b':
        return sentry.layout
    elif pathname == '/em-admin':
        return em_admin.layout
    # elif pathname == '/dashboard':
    #     return dashboard.layout
    # elif pathname == '/signin':
    #     return signin.layout
    # elif pathname == '/signin2':
    #     return signin2.layout
    # elif pathname == '/photos':
    #     return photos.layout
    else:
        return '404'

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=1111)
