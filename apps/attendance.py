import os
import json
import csv
import time
import base64
import io
import urllib.parse
from datetime import datetime
import pandas as pd
import qrcode
import dash
from dash import html, dcc, callback_context
from dash.dependencies import Input, Output, State, MATCH, ALL
import dash_bootstrap_components as dbc
import plotly.express as px
import plotly.graph_objects as go
from app import app as _app

CONFIG_PATH = "./Data/attendance_config.json"
DATA_PATH = "./Data/attendance_data.csv"
QR_PATH = "./assets/attendance_qr.png"

# =============================================================================
# DATA STORE HELPERS
# =============================================================================

def load_attendance_config():
    if not os.path.exists(CONFIG_PATH):
        return {"qr_base_url": "http://127.0.0.1:2222"}
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"qr_base_url": "http://127.0.0.1:2222"}

def save_attendance_config(config):
    os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

def load_attendance_data():
    if not os.path.exists(DATA_PATH):
        return pd.DataFrame(columns=[
            "Timestamp", "Class", "Emp_Code", "Name", "Dept", "Designation", "Mail", "Contact_Number", "Reporting_Manager_Mail"
        ])
    try:
        return pd.read_csv(DATA_PATH, encoding="utf-8")
    except Exception:
        return pd.DataFrame(columns=[
            "Timestamp", "Class", "Emp_Code", "Name", "Dept", "Designation", "Mail", "Contact_Number", "Reporting_Manager_Mail"
        ])

def save_attendance_data(df):
    os.makedirs(os.path.dirname(DATA_PATH), exist_ok=True)
    df.to_csv(DATA_PATH, index=False, encoding="utf-8")

def generate_local_qr(url):
    os.makedirs(os.path.dirname(QR_PATH), exist_ok=True)
    img = qrcode.make(url)
    img.save(QR_PATH)

# =============================================================================
# MOBILE FORM & DASHBOARD BUILDERS
# =============================================================================

def build_attendance_form_page(class_name):
    class_display_name = class_name if class_name else "General Attendance"
    
    form_layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.Div([
                            html.Div(
                                html.I(className="bi bi-qr-code-scan text-primary", style={"fontSize": "3rem"}),
                                style={"marginBottom": "10px"}
                            ),
                            html.H3("TQM Attendance Form", className="fw-bold mb-1", style={"color": "#0d6efd"}),
                            html.H5(f"Class: {class_display_name}", className="fw-bold text-success mb-3"),
                            html.P("Please fill in your details below to submit attendance.", className="text-muted small mb-4"),
                        ], className="text-center"),
                        
                        # Store class_name in a hidden store to capture it on submit
                        dcc.Store(id="att-form-class-name-store", data=class_name),
                        
                        html.Div([
                            # Emp code
                            html.Div([
                                dbc.Label("Emp code *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-empid", placeholder="Enter Employee Code", type="text", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Name
                            html.Div([
                                dbc.Label("Name *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-name", placeholder="Enter your full name", type="text", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Dept
                            html.Div([
                                dbc.Label("Dept *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-dept", placeholder="Enter Department", type="text", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Designation
                            html.Div([
                                dbc.Label("Designation *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-designation", placeholder="Enter Designation", type="text", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Mail
                            html.Div([
                                dbc.Label("Mail *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-mail", placeholder="Enter Email Address", type="email", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Contact number
                            html.Div([
                                dbc.Label("Contact number *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-contact", placeholder="Enter Contact Number", type="tel", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            # Reporting manager mail id
                            html.Div([
                                dbc.Label("Reporting manager mail id *", className="fw-semibold text-secondary small"),
                                dbc.Input(id="att-form-rep-manager-mail", placeholder="Enter Manager Email", type="email", className="py-2", style={"borderRadius": "8px"})
                            ], className="mb-3"),
                            
                            html.Div(id="att-form-alert"),
                            
                            dbc.Button(
                                "Submit Attendance",
                                id="att-form-submit-btn",
                                color="primary",
                                className="w-100 py-3 fw-bold shadow-sm mt-3",
                                style={"borderRadius": "12px", "fontSize": "16px"}
                            )
                        ], id="att-form-fields-wrapper")
                        
                    ], className="p-4")
                ], className="shadow-lg border-0 my-4", style={"borderRadius": "20px", "backgroundColor": "#ffffff"})
            ], xs=12, sm=10, md=8, lg=6, className="mx-auto")
        ], className="justify-content-center min-vh-100 align-items-center g-0", style={"backgroundColor": "#f4f7fc", "margin": "0", "padding": "10px"})
    ], fluid=True, style={"padding": "0"})
    
    return form_layout


def build_attendance_dashboard_page():
    tabs = dbc.Tabs([
        dbc.Tab(label="✍️ Log Attendance", tab_id="tab-manual", label_style={"fontWeight": "600"}),
        dbc.Tab(label="📱 QR Code", tab_id="tab-qr", label_style={"fontWeight": "600"}),
        dbc.Tab(label="📊 Analytics & History", tab_id="tab-analytics", label_style={"fontWeight": "600"})
    ], id="att-dashboard-tabs", active_tab="tab-manual", className="mb-4")
    
    dashboard_layout = dbc.Container([
        dbc.Row([
            dbc.Col([
                html.H2("📊 Attendance Management System", className="fw-bold mb-1", style={"color": "#0d47a1"}),
                html.P("Log attendance records, generate class-specific QR codes, and view class statistics.", className="text-muted mb-4"),
                tabs,
                html.Div(id="att-tab-content-container")
            ], width=12)
        ])
    ], fluid=True, className="py-2")
    
    return dashboard_layout


def render_tab_content(active_tab):
    if active_tab == "tab-manual":
        # Direct in-app manual form containing all 8 fields
        manual_card = dbc.Card([
            dbc.CardBody([
                html.H4("✍️ Log In-App Attendance", className="fw-bold mb-3", style={"color": "#0d6efd"}),
                html.P("Directly submit attendance for a student/employee from this interface.", className="text-muted small mb-4"),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Name of the class *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-class", placeholder="e.g. Logistics", type="text", className="mb-3")
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Emp code *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-empid", placeholder="e.g. EMP1023", type="text", className="mb-3")
                    ], md=6),
                ]),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Name *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-name", placeholder="John Doe", type="text", className="mb-3")
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Dept *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-dept", placeholder="e.g. Operation", type="text", className="mb-3")
                    ], md=6),
                ]),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Designation *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-designation", placeholder="e.g. Executive", type="text", className="mb-3")
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Mail *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-mail", placeholder="john.doe@email.com", type="email", className="mb-3")
                    ], md=6),
                ]),
                
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Contact number *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-contact", placeholder="Enter Phone Number", type="tel", className="mb-3")
                    ], md=6),
                    dbc.Col([
                        dbc.Label("Reporting manager mail id *", className="fw-semibold text-secondary small"),
                        dbc.Input(id="att-manual-rep-manager-mail", placeholder="manager@email.com", type="email", className="mb-3")
                    ], md=6),
                ]),
                
                html.Div(id="att-manual-alert"),
                dbc.Button("Log Attendance Entry", id="att-manual-submit-btn", color="primary", className="fw-semibold w-100 mt-2", style={"borderRadius": "8px"})
            ], className="p-4")
        ], className="shadow border-0", style={"borderRadius": "16px"})
        
        return manual_card
        
    elif active_tab == "tab-qr":
        target_url ="https://forms.cloud.microsoft/Pages/ResponsePage.aspx?id=6_JQEoRHI0KY3NbjNEVWXKUql6pvvYBInizI0i5PKBNURTlRU09KS1VMWllJVVE1T1NWNURMSkJFRi4u"
        
        # Generate base64 QR code image
        try:
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(target_url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode()
            qr_src = f"data:image/png;base64,{img_str}"
        except Exception as e:
            qr_src = ""
            print("QR generation error:", e)

        qr_card = dbc.Card([
            dbc.CardBody([
                html.H4("📱 QR Code", className="fw-bold mb-2", style={"color": "#2a9d8f"}),
                html.P("Scan the QR code below to access the attendance form.", className="text-muted small mb-4"),
                
                html.Div([
                    html.Img(
                        src=qr_src,
                        className="img-fluid shadow-sm border mb-3",
                        style={"borderRadius": "16px", "padding": "15px", "backgroundColor": "#ffffff", "maxWidth": "240px"}
                    )
                ], className="text-center"),
                
                html.Div([
                    html.B("Attendance Form Link: "),
                    html.A(target_url, href=target_url, target="_blank", className="text-break")
                ], className="text-center text-muted small mt-2")
            ], className="p-4")
        ], className="shadow border-0", style={"borderRadius": "16px"})
        
        return qr_card
        
    elif active_tab == "tab-analytics":
        df = load_attendance_data()
        unique_classes = ["All"]
        if not df.empty and "Class" in df.columns:
            unique_classes += sorted(list(df["Class"].dropna().unique()))
            
        class_options = [{"label": c, "value": c} for c in unique_classes]
        
        filter_card = dbc.Card([
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        dbc.Label("Filter by Class", className="fw-semibold text-secondary small"),
                        dcc.Dropdown(id="att-analytics-class-filter", options=class_options, value="All", placeholder="Select Class")
                    ], md=4, className="mb-2"),
                    dbc.Col([
                        dbc.Label("Filter by Date", className="fw-semibold text-secondary small"),
                        dcc.DatePickerSingle(
                            id="att-analytics-date-filter",
                            display_format="DD-MM-YYYY",
                            placeholder="All Dates",
                            className="w-100"
                        )
                    ], md=4, className="mb-2"),
                    dbc.Col([
                        dbc.Label("Actions", className="fw-semibold text-secondary transparent small", style={"color": "transparent"}),
                        dbc.Button(
                            [html.I(className="bi bi-arrow-clockwise me-1"), "Refresh Data"],
                            id="att-analytics-refresh-btn",
                            color="info",
                            className="fw-semibold w-100"
                        )
                    ], md=4, className="mb-2"),
                ], className="align-items-end")
            ], className="py-3 px-4")
        ], className="shadow-sm border-0 mb-4", style={"borderRadius": "12px", "backgroundColor": "#f8fafc"})
        
        charts_row = dbc.Row([
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id="att-chart-class-rate")
                    ])
                ], className="shadow-sm border-0 mb-4", style={"borderRadius": "14px"})
            ], lg=6),
            dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        dcc.Graph(id="att-chart-trend")
                    ])
                ], className="shadow-sm border-0 mb-4", style={"borderRadius": "14px"})
            ], lg=6)
        ])
        
        table_card = dbc.Card([
            dbc.CardHeader([
                html.H5("📋 Attendance Submissions History", className="fw-bold mb-0 text-white")
            ], className="bg-primary text-white py-3", style={"borderTopLeftRadius": "14px", "borderTopRightRadius": "14px"}),
            dbc.CardBody([
                html.Div(id="att-analytics-table-container", style={"overflowX": "auto"})
            ], className="p-0")
        ], className="shadow border-0 mb-4", style={"borderRadius": "14px"})
        
        export_btn = dbc.Button(
            [html.I(className="bi bi-download me-2"), "Download Complete Attendance CSV"],
            id="att-export-csv-btn",
            color="success",
            className="fw-bold py-2 shadow-sm mb-4",
            style={"borderRadius": "8px"}
        )
        
        return html.Div([
            filter_card,
            charts_row,
            table_card,
            html.Div(export_btn, className="text-end"),
            dcc.Download(id="att-export-download")
        ])

# =============================================================================
# ANALYTICS GRAPH BUILDERS
# =============================================================================

def build_analytics_table(class_filter, date_filter):
    df = load_attendance_data()
    if df.empty:
        return html.Div("No records found.", className="p-4 text-center text-muted")
        
    if class_filter and class_filter != "All":
        df = df[df["Class"] == class_filter]
        
    if date_filter:
        try:
            dt_val = datetime.strptime(date_filter, "%Y-%m-%d").date()
            df = df[df["Timestamp"].map(lambda x: datetime.strptime(str(x).split()[0], "%d-%m-%Y").date() == dt_val)]
        except Exception as e:
            print("Table date filter parsing failed:", e)
            
    if df.empty:
        return html.Div("No records match the active filters.", className="p-4 text-center text-muted")
        
    try:
        df["dt_parsed"] = pd.to_datetime(df["Timestamp"], format="%d-%m-%Y %H:%M:%S")
        df = df.sort_values("dt_parsed", ascending=False)
        df = df.drop(columns=["dt_parsed"])
    except Exception:
        df = df.iloc[::-1]
        
    table_rows = []
    df_preview = df.head(100)
    for idx, row in df_preview.iterrows():
        ts = row.get("Timestamp", "")
        c = row.get("Class", "")
        empid = row.get("Emp_Code", "")
        name = row.get("Name", "")
        dept = row.get("Dept", "")
        desig = row.get("Designation", "")
        mail = row.get("Mail", "")
        contact = row.get("Contact_Number", "")
        rep_mail = row.get("Reporting_Manager_Mail", "")
        
        table_rows.append(
            html.Tr([
                html.Td(ts, className="align-middle text-muted small"),
                html.Td(c, className="align-middle fw-semibold"),
                html.Td(empid, className="align-middle fw-semibold"),
                html.Td(name, className="align-middle"),
                html.Td(dept, className="align-middle"),
                html.Td(desig, className="align-middle"),
                html.Td(mail, className="align-middle text-muted small"),
                html.Td(contact, className="align-middle"),
                html.Td(rep_mail, className="align-middle text-muted small"),
                html.Td(
                    dbc.Button(
                        html.I(className="bi bi-trash"),
                        id={"type": "att-delete-record-btn", "timestamp": ts, "name": name},
                        color="danger",
                        size="sm",
                        className="py-1 px-2 border-0"
                    ),
                    className="align-middle text-center"
                )
            ])
        )
        
    table_header = html.Thead([
        html.Tr([
            html.Th("Timestamp", style={"width": "150px"}),
            html.Th("Class", style={"width": "120px"}),
            html.Th("Emp code", style={"width": "110px"}),
            html.Th("Name"),
            html.Th("Dept", style={"width": "110px"}),
            html.Th("Designation", style={"width": "120px"}),
            html.Th("Mail"),
            html.Th("Contact number"),
            html.Th("Reporting manager mail id"),
            html.Th("Action", className="text-center", style={"width": "80px"})
        ], className="table-light")
    ])
    
    table = dbc.Table([
        table_header,
        html.Tbody(table_rows)
    ], striped=True, hover=True, bordered=True, className="mb-0")
    
    return table


def build_analytics_charts(class_filter):
    df = load_attendance_data()
    
    empty_fig = go.Figure().update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        margin=dict(l=0, r=0, t=40, b=0), height=300
    )
    
    if df.empty:
        return empty_fig, empty_fig
        
    try:
        df["Date_Only"] = df["Timestamp"].map(lambda x: str(x).split()[0])
    except Exception:
        df["Date_Only"] = datetime.now().strftime("%d-%m-%Y")
        
    class_counts = df.groupby("Class").size().reset_index(name="Attendance_Count")
    
    fig_bar = px.bar(
        class_counts,
        x="Class",
        y="Attendance_Count",
        title="Attendance Count by Class",
        labels={"Class": "Class Name", "Attendance_Count": "Count"},
        color="Class",
        color_discrete_sequence=["#0d6efd", "#1a73e8", "#2a9d8f", "#e76f51", "#264653"]
    )
    fig_bar.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50, b=40),
        height=320,
        showlegend=False,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#f1f5f9")
    )
    
    trend_data = df.groupby(["Date_Only", "Class"]).size().reset_index(name="Daily_Count")
    
    try:
        trend_data["dt_sort"] = pd.to_datetime(trend_data["Date_Only"], format="%d-%m-%Y")
        trend_data = trend_data.sort_values("dt_sort")
        trend_data = trend_data.drop(columns=["dt_sort"])
    except Exception:
        pass
        
    if class_filter and class_filter != "All":
        trend_data = trend_data[trend_data["Class"] == class_filter]
        
    fig_line = px.line(
        trend_data,
        x="Date_Only",
        y="Daily_Count",
        color="Class",
        title="Daily Attendance Trend (Submissions Count)",
        labels={"Date_Only": "Date", "Daily_Count": "Count", "Class": "Class Name"},
        markers=True,
        color_discrete_sequence=["#0d6efd", "#1a73e8", "#2a9d8f", "#e76f51", "#264653"]
    )
    fig_line.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=20, t=50, b=40),
        height=320,
        xaxis=dict(showgrid=False),
        yaxis=dict(gridcolor="#f1f5f9"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    return fig_bar, fig_line

# =============================================================================
# ROUTING MAIN LAYOUT
# =============================================================================

layout = html.Div([
    dcc.Location(id="attendance-url-loc", refresh=False),
    html.Div(id="attendance-page-content")
])

# =============================================================================
# CALLBACK ROUTER
# =============================================================================

@_app.callback(
    Output("attendance-page-content", "children"),
    Input("attendance-url-loc", "pathname"),
    Input("attendance-url-loc", "search")
)
def render_attendance_page(pathname, search):
    if pathname == "/attendance-form":
        class_name = ""
        if search:
            parsed = urllib.parse.parse_qs(search.lstrip("?"))
            class_name = parsed.get("class", [""])[0]
        return build_attendance_form_page(class_name)
    else:
        return build_attendance_dashboard_page()

# =============================================================================
# ADMIN DASHBOARD CALLBACKS
# =============================================================================

@_app.callback(
    Output("att-tab-content-container", "children"),
    Input("att-dashboard-tabs", "active_tab")
)
def render_tab_content_callback(active_tab):
    return render_tab_content(active_tab)


# @_app.callback(
#     Output("att-qr-alert", "children"),
#     Output("att-qr-output-container", "children"),
#     Input("att-save-qr-btn", "n_clicks"),
#     State("att-qr-base-url", "value"),
#     State("att-qr-class-input", "value"),
#     prevent_initial_call=True
# )
# def save_qr_url_config(n_clicks, base_url_val, class_val):
#     base_url = str(base_url_val).strip().rstrip("/")
#     class_name = str(class_val).strip()
#     
#     if not base_url:
#         return dbc.Alert("Base URL cannot be empty", color="danger"), dash.no_update
#     if not class_name:
#         return dbc.Alert("Class Name is required *", color="danger"), dash.no_update
# 
#     config = load_attendance_config()
#     config["qr_base_url"] = base_url
#     save_attendance_config(config)
# 
#     # Construct the form URL prefilled with the class parameter
#     form_url = f"{base_url}/attendance-form?class={urllib.parse.quote(class_name)}"
#     
#     try:
#         generate_local_qr(form_url)
#     except Exception as e:
#         return dbc.Alert(f"Failed to generate QR: {e}", color="danger"), dash.no_update
#         
#     qr_preview = html.Div([
#         html.Div([
#             html.Img(
#                 src=f"/assets/attendance_qr.png?t={int(time.time())}",
#                 className="img-fluid shadow-sm border mb-3",
#                 style={"borderRadius": "16px", "padding": "15px", "backgroundColor": "#ffffff", "maxWidth": "240px"}
#             )
#         ]),
#         html.P([
#             html.B("Prefilled Class Form Link: "),
#             html.A(form_url, href=form_url, target="_blank", className="text-break")
#         ], className="text-muted small mt-2"),
#     ])
#         
#     return (
#         dbc.Alert(f"QR Code generated successfully for class: {class_name} ✔", color="success", dismissable=True),
#         qr_preview
#     )


@_app.callback(
    Output("att-manual-alert", "children"),
    Output("att-manual-empid", "value"),
    Output("att-manual-name", "value"),
    Output("att-manual-dept", "value"),
    Output("att-manual-designation", "value"),
    Output("att-manual-mail", "value"),
    Output("att-manual-contact", "value"),
    Output("att-manual-rep-manager-mail", "value"),
    Input("att-manual-submit-btn", "n_clicks"),
    State("att-manual-class", "value"),
    State("att-manual-empid", "value"),
    State("att-manual-name", "value"),
    State("att-manual-dept", "value"),
    State("att-manual-designation", "value"),
    State("att-manual-mail", "value"),
    State("att-manual-contact", "value"),
    State("att-manual-rep-manager-mail", "value"),
    prevent_initial_call=True
)
def submit_manual_attendance(n_clicks, class_name, empid, name, dept, desig, mail, contact, rep_mail):
    if not class_name or not str(class_name).strip():
        return dbc.Alert("Name of the class is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not empid or not str(empid).strip():
        return dbc.Alert("Emp code is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not name or not str(name).strip():
        return dbc.Alert("Name is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not dept or not str(dept).strip():
        return dbc.Alert("Dept is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not desig or not str(desig).strip():
        return dbc.Alert("Designation is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not mail or not str(mail).strip():
        return dbc.Alert("Mail is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not contact or not str(contact).strip():
        return dbc.Alert("Contact number is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update
    if not rep_mail or not str(rep_mail).strip():
        return dbc.Alert("Reporting manager mail id is required *", color="danger"), dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update, dash.no_update

    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")

    df = load_attendance_data()
    new_row = {
        "Timestamp": timestamp,
        "Class": str(class_name).strip(),
        "Emp_Code": str(empid).strip(),
        "Name": str(name).strip(),
        "Dept": str(dept).strip(),
        "Designation": str(desig).strip(),
        "Mail": str(mail).strip(),
        "Contact_Number": str(contact).strip(),
        "Reporting_Manager_Mail": str(rep_mail).strip()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_attendance_data(df)
    
    return dbc.Alert("Attendance logged successfully ✔", color="success", dismissable=True), "", "", "", "", "", "", ""

# =============================================================================
# ANALYTICS CHARTS & TABLE DYNAMIC REFRESH CALLBACK
# =============================================================================

@_app.callback(
    Output("att-chart-class-rate", "figure"),
    Output("att-chart-trend", "figure"),
    Output("att-analytics-table-container", "children"),
    Input("att-analytics-class-filter", "value"),
    Input("att-analytics-date-filter", "date"),
    Input("att-analytics-refresh-btn", "n_clicks"),
    Input("att-manual-submit-btn", "n_clicks"),
    Input({"type": "att-delete-record-btn", "timestamp": ALL, "name": ALL}, "n_clicks"),
    prevent_initial_call=False
)
def update_analytics_dashboard(class_filter, date_filter, refresh_clicks, manual_clicks, delete_clicks):
    ctx = dash.callback_context
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0] if ctx.triggered else ""
    
    if "att-delete-record-btn" in trigger_id:
        try:
            triggered_dict = json.loads(trigger_id)
            target_ts = triggered_dict.get("timestamp")
            target_name = triggered_dict.get("name")
            
            df = load_attendance_data()
            if not df.empty:
                mask = (df["Timestamp"] == target_ts) & (df["Name"] == target_name)
                df = df[~mask]
                save_attendance_data(df)
        except Exception as e:
            print("Failed to delete record:", e)
            
    fig_bar, fig_line = build_analytics_charts(class_filter)
    table = build_analytics_table(class_filter, date_filter)
    
    return fig_bar, fig_line, table


@_app.callback(
    Output("att-export-download", "data"),
    Input("att-export-csv-btn", "n_clicks"),
    prevent_initial_call=True
)
def export_attendance_csv(n_clicks):
    if not n_clicks:
        return dash.no_update
        
    df = load_attendance_data()
    return dcc.send_data_frame(df.to_csv, "attendance_records_export.csv", index=False)

# =============================================================================
# MOBILE FORM SUBMISSION CALLBACKS
# =============================================================================

@_app.callback(
    Output("att-form-alert", "children"),
    Output("att-form-fields-wrapper", "children"),
    Input("att-form-submit-btn", "n_clicks"),
    State("att-form-class-name-store", "data"),
    State("att-form-empid", "value"),
    State("att-form-name", "value"),
    State("att-form-dept", "value"),
    State("att-form-designation", "value"),
    State("att-form-mail", "value"),
    State("att-form-contact", "value"),
    State("att-form-rep-manager-mail", "value"),
    prevent_initial_call=True
)
def submit_attendance_form(n_clicks, class_name, empid, name, dept, desig, mail, contact, rep_mail):
    if not empid or not str(empid).strip():
        return dbc.Alert("Emp code is required *", color="danger"), dash.no_update
    if not name or not str(name).strip():
        return dbc.Alert("Name is required *", color="danger"), dash.no_update
    if not dept or not str(dept).strip():
        return dbc.Alert("Dept is required *", color="danger"), dash.no_update
    if not desig or not str(desig).strip():
        return dbc.Alert("Designation is required *", color="danger"), dash.no_update
    if not mail or not str(mail).strip():
        return dbc.Alert("Mail is required *", color="danger"), dash.no_update
    if not contact or not str(contact).strip():
        return dbc.Alert("Contact number is required *", color="danger"), dash.no_update
    if not rep_mail or not str(rep_mail).strip():
        return dbc.Alert("Reporting manager mail id is required *", color="danger"), dash.no_update

    class_val = str(class_name).strip() if class_name else "General"
    timestamp = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    
    df = load_attendance_data()
    new_row = {
        "Timestamp": timestamp,
        "Class": class_val,
        "Emp_Code": str(empid).strip(),
        "Name": str(name).strip(),
        "Dept": str(dept).strip(),
        "Designation": str(desig).strip(),
        "Mail": str(mail).strip(),
        "Contact_Number": str(contact).strip(),
        "Reporting_Manager_Mail": str(rep_mail).strip()
    }
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    save_attendance_data(df)
    
    success_view = html.Div([
        html.Div(
            html.I(className="bi bi-check-circle-fill text-success", style={"fontSize": "5rem"}),
            className="text-center mb-3"
        ),
        html.H3("Attendance Marked!", className="fw-bold text-center text-success mb-2"),
        html.P(f"Thank you, {str(name).strip()}. Your attendance for {class_val} has been successfully logged.", className="text-muted text-center mb-4"),
        dbc.Button("Submit Another Entry", id="att-submit-another-btn", color="outline-primary", className="w-100 py-2", style={"borderRadius": "8px"})
    ], className="py-4")
    
    return "", success_view


@_app.callback(
    Output("att-form-fields-wrapper", "children", allow_duplicate=True),
    Input("att-submit-another-btn", "n_clicks"),
    prevent_initial_call=True
)
def reset_attendance_form(n_clicks):
    if not n_clicks:
        return dash.no_update
        
    return [
        html.Div([
            dbc.Label("Emp code *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-empid", placeholder="Enter Employee Code", type="text", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Name *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-name", placeholder="Enter your full name", type="text", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Dept *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-dept", placeholder="Enter Department", type="text", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Designation *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-designation", placeholder="Enter Designation", type="text", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Mail *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-mail", placeholder="Enter Email Address", type="email", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Contact number *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-contact", placeholder="Enter Contact Number", type="tel", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div([
            dbc.Label("Reporting manager mail id *", className="fw-semibold text-secondary small"),
            dbc.Input(id="att-form-rep-manager-mail", placeholder="Enter Manager Email", type="email", className="py-2", style={"borderRadius": "8px"})
        ], className="mb-3"),
        html.Div(id="att-form-alert"),
        dbc.Button(
            "Submit Attendance",
            id="att-form-submit-btn",
            color="primary",
            className="w-100 py-3 fw-bold shadow-sm mt-3",
            style={"borderRadius": "12px", "fontSize": "16px"}
        )
    ]
