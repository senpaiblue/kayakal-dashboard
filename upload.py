from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import dash
from app import app
from dash import callback_context, no_update


from apps import a, b, c, e, sentry, lg, projects_upload, j1_upload, qmml_admin, em_admin, kayakalp_admin, red_tag_admin, greenery_admin, opl_pokayoke_upload, dwm_upload
# from apps.logistics_migration import migrate_logistics_deleted_to_logistics

# One-time safe data cleanup for renamed Logistics department.
# migrate_logistics_deleted_to_logistics()

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
    """Admin sidebar navigation"""

    def btn(label, icon, href, key):
        is_active = active == key
        return html.A(
            [
                html.I(className=icon + " sidebar-icon"),
                html.Span(label),
            ],
            className="sidebar-btn active" if is_active else "sidebar-btn",
            href=href,
        )

    return html.Div([
        html.Div([
            html.Img(src="/assets/logo.jpg", className="sidebar-logo-img"),
            html.H4("Admin Panel", className="sidebar-app-title", style={"margin": "0", "marginLeft": "10px", "fontWeight": "bold", "color": "#1a1a1a", "fontSize": "16px"})
        ], className="sidebar-header"),
        html.Div([
            btn("5s Photos", "fa-solid fa-camera", "/a", "a"),
            btn("Kaizen File", "fa-solid fa-file", "/b", "b"),
            btn("Gallery Photos", "fa-regular fa-image", "/c", "c"),
            btn("Spotlights & Pwd Mgmt", "fa-solid fa-star", "/d", "d"),
            btn("Training, Events & News", "fa-solid fa-graduation-cap", "/e", "e"),
            btn("Projects Upload", "fa-solid fa-upload", "/projects-upload", "projects-upload"),
            btn("J1 Upload", "fa-solid fa-file-upload", "/j1-upload", "j1-upload"),
            btn("Visitors Monitoring", "fa-solid fa-graduation-cap", "/lg", "lg"),
            btn("QMML Upload", "fa-solid fa-file-circle-plus", "/qmml-upload", "qmml-upload"),
            btn("Emission Upload", "fa-solid fa-cloud-arrow-up", "/em-admin", "em-admin"),
            btn("Kayakalp", "fa-solid fa-user-shield", "/kayakalp-admin", "kayakalp-admin"),
            btn("OPL/Poka Yoke Upload", "fa-solid fa-file-excel", "/opl-upload", "opl-upload"),
            btn("Daily Management Upload", "fa-solid fa-clock-rotate-left", "/dwm-upload", "dwm-upload"),
            html.Div(style={"flexGrow": "1"}),
            btn("Logout", "fa-solid fa-right-from-bracket", "/logout", "logout"),
        ], className="sidebar-nav")
    ], className="sidebar-container")




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

    def with_sidebar(active, page_layout):
        return dbc.Container([
            dbc.Row([
                dbc.Col(nav_bar(active), lg=2, md=3, sm=12, className="sidebar-col-custom", style={"padding": "0"}),
                dbc.Col(page_layout, lg=10, md=9, sm=12, className="main-content-col-custom", style={"padding": "20px", "height": "100vh", "overflowY": "auto", "backgroundColor": "#f4f7fc"})
            ], className="g-0")
        ], fluid=True, className="app-layout-wrapper", style={"padding": "0", "margin": "0"})

    if pathname == "/a":
        return with_sidebar("a", sentry.layout)
    elif pathname == "/b":
        return with_sidebar("b", a.layout)
    elif pathname == "/c":
        return with_sidebar("c", c.layout)
    elif pathname == "/d":
        return with_sidebar("d", b.layout)
    elif pathname == "/e":
        return with_sidebar("e", e.layout)
    elif pathname == "/projects-upload":
        return with_sidebar("projects-upload", projects_upload.layout)
    elif pathname == "/j1-upload":
        return with_sidebar("j1-upload", j1_upload.layout)
    elif pathname == "/lg":
        return with_sidebar("lg", lg.layout)
    elif pathname == "/qmml-upload":
        return with_sidebar("qmml-upload", qmml_admin.layout)
    elif pathname == "/em-admin":
        return with_sidebar("em-admin", em_admin.layout)
    elif pathname == "/kayakalp-admin":
        return with_sidebar("kayakalp-admin", kayakalp_admin.layout())
    elif pathname == "/opl-upload":
        return with_sidebar("opl-upload", opl_pokayoke_upload.layout)
    elif pathname == "/dwm-upload":
        return with_sidebar("dwm-upload", dwm_upload.layout)
    return with_sidebar("a", sentry.layout)

# ---------------- LOGIN LOGIC ----------------
@app.callback(
    Output("login-status", "data"),
    Output("login-msg", "children"),
    Output("url", "pathname"),
    Input("login-btn", "n_clicks"),
    State("username", "value"),
    State("password", "value"),
    prevent_initial_call=True,
)
def handle_login(n_clicks, username, password):
    if not n_clicks:
        return no_update, no_update, no_update

    if username in USERS and USERS[username] == password:
        return True, "", "/a"

    return False, "Invalid username or password", "/"


@app.callback(
    Output("login-status", "data", allow_duplicate=True),
    Input("url", "pathname"),
    prevent_initial_call=True,
)
def handle_logout(pathname):
    if pathname == "/logout":
        return False

    return no_update



# ---------------- RUN ----------------
def _is_port_in_use(port: int) -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) == 0

def _run_server():
    port = 1111
    while port < 1120:
        if not _is_port_in_use(port):
            break
        port += 1
    else:
        port = 1111  # fallback, will raise if still in use
    print(f"Starting server on http://0.0.0.0:{port}/")
    app.run(debug=False, host="0.0.0.0", port=port)

if __name__ == "__main__":
    _run_server()
