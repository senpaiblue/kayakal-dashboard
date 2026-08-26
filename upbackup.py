from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash
from server import app
from dash import callback_context, no_update


from apps import a, b, c, e,sentry,lg,projects_upload
def app_header():
    return html.Div(
        "Admin Panel TQM-vjnr Dashboard",
        className="app-title",
    )

USERS = {
    "admin": "12345",
    "TQM": "12345",
    "Bhaskar": "Hello",
    "Abhi": "12345",
}

# ---------------- LOGIN PAGE ----------------
login_layout = dbc.Container(
    [
        html.H2("Admin Panel TQM-vjnr Dashboard", className="text-center mt-4"),
        html.H5("Secure Login", className="text-center text-muted mb-4"),

        dbc.Input(id="username", placeholder="Username", type="text", className="mt-3"),
        dbc.Input(id="password", placeholder="Password", type="password", className="mt-2"),
        dbc.Button("Login", id="login-btn", color="primary", className="mt-3 w-100"),
        html.Div(id="login-msg", className="text-danger mt-2"),
    ],
    style={"maxWidth": "420px"},
)


# ---------------- TOP NAV BAR ----------------
def nav_bar(active):
    def btn(label, icon, href, key, extra_class=""):
        return html.A(
            [
                html.I(className=icon),
                html.Div(label)
            ],
            href=href,
            className=f"nav-btn {'active' if active == key else ''} {extra_class}",
        )

    return html.Div(
        [
            # LEFT
            html.Div(
                [
                    html.Div("Admin Panel", className="nav-title"),
                    html.Div("If any issue contact Developer", className="nav-subtitle"),
                ],
                className="nav-left",
            ),

            # RIGHT
            html.Div(
                [
                    btn("5s Photos", "fa-solid fa-camera", "/a", "a"),
                    btn("Kaizen File", "fa-solid fa-file", "/b", "b"),
                    btn("Gallery Photos", "fa-regular fa-image", "/c", "c"),
                    btn("Spotlights & Password Management", "fa-solid fa-star", "/d", "d"),
                    btn("Training, Events & Newsletter", "fa-solid fa-graduation-cap", "/e", "e"),
                    btn("Projects Upload", "fa-solid fa-upload", "/projects-upload", "projects-upload"),
                    btn("Visitors Monitoring", "fa-solid fa-graduation-cap", "/lg", "lg"),
                    btn("Logout", "fa-solid fa-right-from-bracket", "/logout", "logout", "logout-btn"),
                ],
                className="nav-right",
            ),
        ],
        className="nav-container align-left",
    )




# ---------------- MAIN APP LAYOUT ----------------
app.layout = html.Div(
    [
        dcc.Location(id="url"),
        dcc.Store(id="login-status", storage_type="session"),
        html.Div(id="page-content"),
    ]
)

# ---------------- PAGE ROUTING ----------------
@app.callback(
    Output("page-content", "children"),
    Input("url", "pathname"),
    State("login-status", "data"),
)
def display_page(pathname, logged_in):

    if pathname == "/logout":
        return login_layout

    if not logged_in:
        return login_layout

    if pathname == "/a":
        return html.Div([nav_bar("a"), sentry.layout])
    elif pathname == "/b":
        return html.Div([nav_bar("b"), a.layout])
    elif pathname == "/c":
        return html.Div([nav_bar("c"), c.layout])
    elif pathname == "/d":
        return html.Div([nav_bar("d"), b.layout])
    elif pathname == "/e":
        return html.Div([nav_bar("e"), e.layout])
    elif pathname == "/projects-upload":
         return html.Div([nav_bar("projects-upload"), projects_upload.layout])   
    elif pathname == "/lg":
        return html.Div([nav_bar("lg"), lg.layout])

    return html.Div([nav_bar("a"), sentry.layout])

# ---------------- LOGIN LOGIC ----------------
@app.callback(
    Output("login-status", "data"),
    Output("login-msg", "children"),
    Output("url", "pathname"),
    Input("login-btn", "n_clicks"),
    Input("url", "pathname"),
    State("username", "value"),
    State("password", "value"),
    State("login-status", "data"),
    prevent_initial_call=True,
)
def auth_handler(n_clicks, pathname, username, password, logged_in):

    ctx = callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

    # ---------- LOGOUT ----------
    if trigger == "url" and pathname == "/logout":
        return False, "", "/"

    # ---------- LOGIN ----------
    if trigger == "login-btn":
        if username in USERS and USERS[username] == password:
            return True, "", "/a"
        return False, "Invalid username or password", "/"


    return no_update, no_update, no_update



# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=False,host='0.0.0.0',port="1111")
