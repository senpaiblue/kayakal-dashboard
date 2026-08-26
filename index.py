import dash_bootstrap_components as dbc
from dash import dcc, html
from dash.dependencies import Input, Output
import dash
from apps import (
    analysis,
    kaizen,
    training,
    reports,
    gallery,
    summary,
    events,
    spotlights,
    news,
    sentry,
    d,
    magazine,
    ng,
    projects,
    comb,
    k5,
    k5_trends,
    em,
    valuecredited,
    value_credited_admin,
    progress,
    progress_admin,
    area_master_admin,
    red_tag_museum,
    red_tag_admin,
    rejection_remarks,
    greenery,
    greenery_admin,
    j1,
    qmml,
    projects_identified_admin,
    projects_identified_display,
    opl_pokayoke,
    solid_waste_management,
    solid_waste_admin,
    red_tag_trends,
    attendance,
    daily_management,
)
from app import server
from app import app
import logging
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(BASE_DIR, 'logs.txt')

log = logging.getLogger('werkzeug')
log.setLevel(logging.INFO)

# Make sure not to duplicate handlers if reloaded
if not any(isinstance(h, logging.FileHandler) for h in log.handlers):
    file_handler = logging.FileHandler(LOG_FILE)
    file_handler.setLevel(logging.INFO)
    # The default werkzeug message contains the exact IP, date, method, and status format needed
    file_handler.setFormatter(logging.Formatter('%(message)s'))
    log.addHandler(file_handler)


def nav_button(label, icon, path, current):
    active = (path == current)

    return html.A(
        [
            html.I(className=f"bi bi-{icon} sidebar-icon"),
            html.Span(label)
        ],
        href=path,
        className="sidebar-btn active" if active else "sidebar-btn"
    )


app.layout = dbc.Container([
    # Required hidden components
    dcc.Location(id='page_navi'),
    dcc.Store(id="selected-zone", storage_type="session"),
    dcc.Store(id="selected-department", storage_type="session"),

    dbc.Row([
        # Sidebar Column
        dbc.Col([
            html.Div([
                html.Div([
                    html.Img(src="/assets/logo.jpg", className="sidebar-logo-img"),
                    html.H4("TQM-vjnr", className="sidebar-app-title", style={"margin": "0", "marginLeft": "10px", "fontWeight": "bold", "color": "#1a1a1a"})
                ], className="sidebar-header"),
                html.Div(id="dynamic-nav", className="sidebar-nav")
            ], className="sidebar-container")
        ], id="sidebar-col", lg=2, md=3, sm=12, className="sidebar-col-custom", style={"padding": "0"}),

        # Main Content Column
        dbc.Col([
            html.Div(id='main_output', className="main-output-container")
        ], id="main-content-col", lg=10, md=9, sm=12, className="main-content-col-custom", style={"padding": "20px", "height": "100vh", "overflowY": "auto", "backgroundColor": "#f4f7fc"})
    ], className="g-0")

], fluid=True, className="app-layout-wrapper", style={"padding": "0", "margin": "0"})
# -------------------------------------------------------------------
# Dynamic Navigation Bar (Highlights Active Page)
# -------------------------------------------------------------------
@app.callback(
    Output("dynamic-nav", "children"),
    Input("page_navi", "pathname")
)
def update_navbar(current_path):

    return html.Div([

        nav_button("Gallery", "house-fill", "/", current_path),
        nav_button("Kaizen", "images", "/kaizen", current_path),
        nav_button("OPL/Poka yoke", "file-earmark-check", "/opl-pokayoke", current_path),
        nav_button("J2 & J3", "diagram-3-fill", "/projects", current_path),
        nav_button("5S", "images", "/sentry", current_path),
        nav_button("Kayakalp 5s", "clipboard-check", "/k5-trends", current_path),
        nav_button("Solid waste management", "trash", "/solid-waste-management", current_path),
        nav_button("Emission Control", "cloud", "/em", current_path),
        nav_button("Nuggets", "check-circle", "/ng", current_path),
        nav_button("Events", "calendar-event", "/events", current_path),
        nav_button("Training", "mortarboard", "/training", current_path),
        nav_button("Spotlights", "stars", "/spotlights", current_path),
        nav_button("Magazines", "book", "/mg", current_path),
        nav_button("Newsletter", "newspaper", "/news", current_path),
        nav_button("J1+", "clipboard-check", "/j1", current_path),
        nav_button("QMML", "bar-chart-line", "/qmml", current_path),
        nav_button("Attendance", "qr-code", "/attendance", current_path),
        nav_button("Daily Management", "clipboard-data-fill", "/daily-management", current_path),
        html.Div(style={"flexGrow": "1"})

    ], className="sidebar-nav")

# -------------------------------------------------------------------
# Sidebar Toggle Callback (Hides sidebar for mobile attendance form)
# -------------------------------------------------------------------
@app.callback(
    Output("sidebar-col", "style"),
    Output("main-content-col", "lg"),
    Output("main-content-col", "md"),
    Output("main-content-col", "style"),
    Input("page_navi", "pathname")
)
def toggle_sidebar_layout(pathname):
    if pathname == "/attendance-form":
        # Fullscreen mobile layout, hide sidebar, remove padding
        return {"display": "none"}, 12, 12, {"padding": "0px", "height": "100vh", "overflowY": "auto", "backgroundColor": "#f4f7fc"}
    # Default layout with sidebar
    return {"display": "block"}, 10, 9, {"padding": "20px", "height": "100vh", "overflowY": "auto", "backgroundColor": "#f4f7fc"}

# -------------------------------------------------------------------
# Page Router
# -------------------------------------------------------------------
@app.callback(Output('main_output', 'children'), Input('page_navi', 'pathname'))
def main_content_loader(pathname):

    if pathname == '/':
        return gallery.layout
    elif pathname == '/kaizen':
        return kaizen.layout
    elif pathname == '/opl-pokayoke':
        return opl_pokayoke.layout
    elif pathname == '/projects':
        return projects.layout
    elif pathname == '/events':
        return events.layout
    elif pathname == '/training':
        return training.layout
    elif pathname == '/reports':
        return reports.layout
    elif pathname == '/summary':
        return summary.layout
    elif pathname == '/spotlights':
        return spotlights.layout
    elif pathname == '/sentry':
        return comb.layout
    elif pathname == '/mg':
        return magazine.layout
    elif pathname == '/news':
        return news.layout
    elif pathname == '/ng':
        return ng.layout
    elif pathname == '/k5':
        return k5.layout
    elif pathname == '/k5-trends':
        return k5_trends.layout
    elif pathname == '/red-tag-trends':
        return red_tag_trends.layout
    elif pathname == '/em':
        return em.layout
    elif pathname == '/valuecredited':
        return valuecredited.layout
    elif pathname == '/progress':
        return progress.layout() if callable(progress.layout) else progress.layout
    elif pathname == '/red_tag_museum':
        return red_tag_museum.layout
    elif pathname == '/greenery':
        return greenery.layout
    elif pathname == '/remarks':
        return rejection_remarks.layout
    elif pathname == '/greenery-admin':
        return greenery_admin.layout
    elif pathname == '/j1':
        return j1.layout
    elif pathname == '/qmml':
        return qmml.layout
    elif pathname == '/attendance' or pathname == '/attendance-form':
        return attendance.layout
    elif pathname == '/solid-waste-management':
        return solid_waste_management.layout
    elif pathname == '/solid-waste-admin':
        return solid_waste_admin.layout
    elif pathname == '/progress-admin':
        return progress_admin.layout
    elif pathname == '/area-master':
        return area_master_admin.layout
    elif pathname == '/red-tag-admin':
        return red_tag_admin.layout
    elif pathname == '/value-credited-admin':
        return value_credited_admin.layout
    elif pathname == '/projects-identified-admin':
        return projects_identified_admin.layout
    elif pathname == '/projects-identified-display':
        return projects_identified_display.layout
    elif pathname == '/daily-management':
        return daily_management.layout() if callable(daily_management.layout) else daily_management.layout
    else:
        return "404 - Page Not Found"



if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=2222)
