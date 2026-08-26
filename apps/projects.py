import dash
from app import app
import pandas as pd
from pathlib import Path
from dash import html, dcc, Input, Output, State, dash_table, ALL, callback_context
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px

CSV_PATH = "./Data/projects_data.csv"

def read_csv_safely(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            return pd.read_csv(path, dtype=str, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to read CSV with any known encoding. Convert file to UTF-8 or CP1252.")
def load_fresh_data():
    """Load fresh data from CSV - called in each callback to get latest data"""
    if not Path(CSV_PATH).exists():
        raise FileNotFoundError(f"CSV not found at {CSV_PATH}")
    
    df = read_csv_safely(CSV_PATH)
    df.columns = df.columns.str.strip()
    return df

# Initial load for layout only
df = load_fresh_data()

# Get unique project titles and remove empty ones
if "Project Title" in df.columns:
    project_titles = df["Project Title"].dropna().unique().tolist()
    project_titles = [title for title in project_titles if str(title).strip()]
else:
    project_titles = []

# Create dropdown options with "All" as first option
dropdown_options = [{"label": "All", "value": "All"}] + [
    {"label": title, "value": title} for title in sorted(project_titles)
]

# Get unique values for other filters
grades = sorted([g for g in df["Grade"].dropna().unique() if str(g).strip()]) if "Grade" in df.columns else []
emails = sorted([e for e in df["E - Mail"].dropna().unique() if str(e).strip()]) if "E - Mail" in df.columns else []
mobiles = sorted([m for m in df["Mobile No."].dropna().unique() if str(m).strip()]) if "Mobile No." in df.columns else []
departments = sorted([d for d in df["Department"].dropna().unique() if str(d).strip()]) if "Department" in df.columns else []
zones = sorted([z for z in df["Zone"].dropna().unique() if str(z).strip()]) if "Zone" in df.columns else []
names = sorted([n for n in df["Name"].dropna().unique() if str(n).strip()]) if "Name" in df.columns else []
employee_nos = sorted([e for e in df["E.No."].dropna().unique() if str(e).strip()]) if "E.No." in df.columns else []

layout = html.Div([
    html.H2("Projects Dashboard", style={"marginBottom": "20px", "color": "#0d6efd"}),
    
    # First Row: Department and Zone
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Department", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="department-dropdown_NEW",
                    options=[{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments],
                    value="All",
                    clearable=False
                )
            ], width=4),
            dbc.Col([
                html.Label("Zone", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="zone-dropdown",
                    options=[{"label": "All", "value": "All"}] + [{"label": z, "value": z} for z in zones],
                    value="All",
                    clearable=False
                )
            ], width=4),
        ]),
    ], className="first-filter-row", style={"marginBottom": "20px", "display": "block", "width": "100%"}),
    
    # Second Row: Name and E.No.
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Name", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="name-dropdown",
                    options=[],
                    value="All",
                    clearable=False
                )
            ], width=4),
            dbc.Col([
                html.Label("Employee No.", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="eno-dropdown",
                    options=[],
                    value="All",
                    clearable=False
                )
            ], width=4),
        ]),
    ], className="second-filter-row", style={"marginBottom": "20px", "display": "block", "width": "100%"}),
    
    # Third Row: Grade, E-mail, Mobile
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Grade", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="grade-dropdown",
                    options=[],
                    value="All",
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                html.Label("E-mail", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="email-dropdown",
                    options=[],
                    value="All",
                    clearable=False
                )
            ], width=3),
            dbc.Col([
                html.Label("Mobile", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="mobile-dropdown",
                    options=[],
                    value="All",
                    clearable=False
                )
            ], width=3),
        ]),
    ], className="third-filter-row", style={"marginBottom": "20px", "display": "block", "width": "100%"}),
    
    # Fourth Row: Project Title
    html.Div([
        dbc.Row([
            dbc.Col([
                html.Label("Project Title", style={"fontWeight": "600", "fontSize": "14px", "marginBottom": "8px", "display": "block"}),
                dcc.Dropdown(
                    id="project-title-dropdown",
                    options=dropdown_options,
                    value="All",
                    clearable=False,
                    optionHeight=80
                )
            ], width=12),
        ]),
    ], className="fourth-filter-row", style={"marginBottom": "20px", "display": "block", "width": "100%"}),
    
    html.Hr(style={"margin": "20px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # GB and BB Statistics Row
    dbc.Row([
        dbc.Col([
            html.H4("Green Belt (GB) Projects", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="gb-chart", style={"height": "300px"})
        ], width=6),
        dbc.Col([
            html.H4("Black Belt (BB) Projects", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="bb-chart", style={"height": "300px"})
        ], width=6)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Vetting Status Charts Row
    dbc.Row([
        dbc.Col([
            html.H4("Vetting Status vs Department", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="vetting-dept-chart", style={"height": "400px"})
        ], width=6),
        dbc.Col([
            html.H4("Vetting Status vs Zone", style={"marginBottom": "15px", "color": "#333", "textAlign": "center"}),
            dcc.Graph(id="vetting-zone-chart", style={"height": "400px"})
        ], width=6)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Department vs Status Graph and Details Side by Side
    dbc.Row([
        dbc.Col([
            html.H4("Department vs Status", style={"marginBottom": "15px", "color": "#333"}),
            dcc.Graph(id="dept-status-graph", style={"height": "500px"})
        ], width=7),
        dbc.Col([
            html.Div(id="department-details", style={"padding": "10px"})
        ], width=5)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
    
    # Zone vs Status Graph and Details Side by Side
    dbc.Row([
        dbc.Col([
            html.H4("Zone vs Status", style={"marginBottom": "15px", "color": "#333"}),
            dcc.Graph(id="zone-status-graph", style={"height": "500px"})
        ], width=7),
        dbc.Col([
            html.Div(id="zone-details", style={"padding": "10px"})
        ], width=5)
    ], style={"marginTop": "20px"}),
    
    html.Hr(style={"margin": "30px 0", "border": "none", "height": "1px", "backgroundColor": "#ddd"}),
   
    html.Div(id="project-summary", style={"marginTop": "20px"}),
    
    # Stores for status filter selections
    dcc.Store(id="dept-status-filter-store", data=None),
    dcc.Store(id="zone-status-filter-store", data=None),
    
    # Download components
    dcc.Download(id="dept-download-excel"),
    dcc.Download(id="zone-download-excel"),
    
    # Interval component to refresh dropdowns every 5 seconds
    dcc.Interval(
        id='interval-refresh',
        interval=5*1000,  # in milliseconds (5 seconds)
        n_intervals=0
    )
    
], style={"padding": "20px", "fontFamily": "Arial"})

@app.callback(
    Output("zone-dropdown", "options"),
    Output("project-title-dropdown", "options"),
    Input("interval-refresh", "n_intervals"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value")
)
def refresh_dropdowns(n_intervals, current_zone, current_project):
    df = load_fresh_data()  # Load fresh data
    
    # Get unique zones
    zones = sorted([z for z in df["Zone"].dropna().unique() if str(z).strip()]) if "Zone" in df.columns else []
    zone_options = [{"label": "All", "value": "All"}] + [{"label": z, "value": z} for z in zones]
    
    # Get unique project titles
    if "Project Title" in df.columns:
        project_titles = df["Project Title"].dropna().unique().tolist()
        project_titles = [title for title in project_titles if str(title).strip()]
        project_options = [{"label": "All", "value": "All"}] + [
            {"label": title, "value": title} for title in sorted(project_titles)
        ]
    else:
        project_options = [{"label": "All", "value": "All"}]
    
    return zone_options, project_options

# Callback to update department dropdown based on zone selection
@app.callback(
    Output("department-dropdown_NEW", "options"),
    Output("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value")
)
def update_department_options(selected_zone):
    df = load_fresh_data()  # Load fresh data
    departments = sorted([d for d in df["Department"].dropna().unique() if str(d).strip()]) if "Department" in df.columns else []

    if selected_zone == "All":
        # Show all departments
        dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments]
        return dept_options, "All"
    else:
        # Filter departments by selected zone
        if "Department" in df.columns and "Zone" in df.columns:
            filtered_depts = df[df["Zone"] == selected_zone]["Department"].dropna().unique()
            filtered_depts = sorted([d for d in filtered_depts if str(d).strip()])
            dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in filtered_depts]
            return dept_options, "All"
        else:
            dept_options = [{"label": "All", "value": "All"}] + [{"label": d, "value": d} for d in departments]
            return dept_options, "All"

# Callback to sync all individual-related filters (Name, E.No., Email, Mobile, Grade)
@app.callback(
    Output("name-dropdown", "options"),
    Output("name-dropdown", "value"),
    Output("eno-dropdown", "options"),
    Output("eno-dropdown", "value"),
    Output("grade-dropdown", "options"),
    Output("grade-dropdown", "value"),
    Output("email-dropdown", "options"),
    Output("email-dropdown", "value"),
    Output("mobile-dropdown", "options"),
    Output("mobile-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
)
def sync_individual_filters(selected_department, selected_zone, selected_name, selected_eno, 
                           selected_grade, selected_email, selected_mobile):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Filter by department if selected
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    # Filter by zone if selected
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    # Get filtered options for all individual fields
    if "Name" in filtered_df.columns:
        filtered_names = filtered_df["Name"].dropna().unique()
        filtered_names = sorted([n for n in filtered_names if str(n).strip()])
        name_options = [{"label": "All", "value": "All"}] + [{"label": n, "value": n} for n in filtered_names]
    else:
        name_options = [{"label": "All", "value": "All"}]
    
    if "E.No." in filtered_df.columns:
        filtered_enos = filtered_df["E.No."].dropna().unique()
        filtered_enos = sorted([e for e in filtered_enos if str(e).strip()])
        eno_options = [{"label": "All", "value": "All"}] + [{"label": e, "value": e} for e in filtered_enos]
    else:
        eno_options = [{"label": "All", "value": "All"}]
    
    if "Grade" in filtered_df.columns:
        filtered_grades = filtered_df["Grade"].dropna().unique()
        filtered_grades = sorted([g for g in filtered_grades if str(g).strip()])
        grade_options = [{"label": "All", "value": "All"}] + [{"label": g, "value": g} for g in filtered_grades]
    else:
        grade_options = [{"label": "All", "value": "All"}]
    
    if "E - Mail" in filtered_df.columns:
        filtered_emails = filtered_df["E - Mail"].dropna().unique()
        filtered_emails = sorted([e for e in filtered_emails if str(e).strip()])
        email_options = [{"label": "All", "value": "All"}] + [{"label": e, "value": e} for e in filtered_emails]
    else:
        email_options = [{"label": "All", "value": "All"}]
    
    if "Mobile No." in filtered_df.columns:
        filtered_mobiles = filtered_df["Mobile No."].dropna().unique()
        filtered_mobiles = sorted([m for m in filtered_mobiles if str(m).strip()])
        mobile_options = [{"label": "All", "value": "All"}] + [{"label": m, "value": m} for m in filtered_mobiles]
    else:
        mobile_options = [{"label": "All", "value": "All"}]
    
    # Initialize return values to "All"
    return_name = "All"
    return_eno = "All"
    return_grade = "All"
    return_email = "All"
    return_mobile = "All"
    
    # Find the individual's complete record based on any selected field
    individual_record = None
    
    if selected_name != "All" and "Name" in df.columns:
        individual_record = df[df["Name"] == selected_name].iloc[0] if len(df[df["Name"] == selected_name]) > 0 else None
    elif selected_eno != "All" and "E.No." in df.columns:
        individual_record = df[df["E.No."] == selected_eno].iloc[0] if len(df[df["E.No."] == selected_eno]) > 0 else None
    elif selected_grade != "All" and "Grade" in df.columns:
        matching = df[df["Grade"] == selected_grade]
        if len(matching) == 1:
            individual_record = matching.iloc[0]
    elif selected_email != "All" and "E - Mail" in df.columns:
        individual_record = df[df["E - Mail"] == selected_email].iloc[0] if len(df[df["E - Mail"] == selected_email]) > 0 else None
    elif selected_mobile != "All" and "Mobile No." in df.columns:
        individual_record = df[df["Mobile No."] == selected_mobile].iloc[0] if len(df[df["Mobile No."] == selected_mobile]) > 0 else None
    
    # If we found an individual record, sync all fields
    if individual_record is not None:
        if "Name" in df.columns and pd.notna(individual_record["Name"]):
            return_name = str(individual_record["Name"])
        if "E.No." in df.columns and pd.notna(individual_record["E.No."]):
            return_eno = str(individual_record["E.No."])
        if "Grade" in df.columns and pd.notna(individual_record["Grade"]):
            return_grade = str(individual_record["Grade"])
        if "E - Mail" in df.columns and pd.notna(individual_record["E - Mail"]):
            return_email = str(individual_record["E - Mail"])
        if "Mobile No." in df.columns and pd.notna(individual_record["Mobile No."]):
            return_mobile = str(individual_record["Mobile No."])
    
    return name_options, return_name, eno_options, return_eno, grade_options, return_grade, email_options, return_email, mobile_options, return_mobile

# Callback to update GB chart
@app.callback(
    Output("gb-chart", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_gb_chart(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    # Filter for GB projects
    if "LSSGB/LSSBB" in filtered_df.columns:
        gb_df = filtered_df[filtered_df["LSSGB/LSSBB"].str.strip().str.startswith("GB", na=False)]
    else:
        gb_df = pd.DataFrame()
    
    if gb_df.empty:
        return go.Figure().add_annotation(
            text="No GB projects found",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )
    
    total_gb = len(gb_df)
    
    # Create status breakdown
    if "Status" in gb_df.columns:
        status_counts = gb_df["Status"].value_counts().sort_values(ascending=True)
        
        # Define color map
        color_map = {
            "Not Initiated": "#e74c3c",
            "Review is pending": "#f39c12",
            "Completed": "#27ae60",
            "dropped": "#95a5a6"
        }
        
        colors = [color_map.get(status, "#3498db") for status in status_counts.index]
        
        # Create horizontal bar chart
        fig = go.Figure(data=[go.Bar(
            y=status_counts.index,
            x=status_counts.values,
            orientation='h',
            marker=dict(color=colors),
            text=status_counts.values,
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"
        )])
        
        fig.update_layout(
            title=dict(
                text=f"<b>Total GB Projects: {total_gb}</b>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Number of Projects",
            yaxis_title="",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=150, r=40, t=60, b=40),
            height=300,
            font=dict(size=13),
            xaxis=dict(
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True
            ),
            yaxis=dict(
                tickfont=dict(size=13)
            )
        )
        
        return fig
    
    return go.Figure()

# Callback to update BB chart
@app.callback(
    Output("bb-chart", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_bb_chart(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    # Filter for BB projects
    if "LSSGB/LSSBB" in filtered_df.columns:
        bb_df = filtered_df[filtered_df["LSSGB/LSSBB"].str.strip().str.startswith("BB", na=False)]
    else:
        bb_df = pd.DataFrame()
    
    if bb_df.empty:
        return go.Figure().add_annotation(
            text="No BB projects found",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )
    
    total_bb = len(bb_df)
    
    # Create status breakdown
    if "Status" in bb_df.columns:
        status_counts = bb_df["Status"].value_counts().sort_values(ascending=True)
        
        # Define color map
        color_map = {
            "Not Initiated": "#e74c3c",
            "Review is pending": "#f39c12",
            "Completed": "#27ae60",
            "dropped": "#95a5a6"
        }
        
        colors = [color_map.get(status, "#3498db") for status in status_counts.index]
        
        # Create horizontal bar chart
        fig = go.Figure(data=[go.Bar(
            y=status_counts.index,
            x=status_counts.values,
            orientation='h',
            marker=dict(color=colors),
            text=status_counts.values,
            textposition='auto',
            textfont=dict(size=14, color='white', family='Arial Black'),
            hovertemplate="<b>%{y}</b><br>Count: %{x}<extra></extra>"
        )])
        
        fig.update_layout(
            title=dict(
                text=f"<b>Total BB Projects: {total_bb}</b>",
                x=0.5,
                xanchor='center',
                font=dict(size=18, color="#2c3e50")
            ),
            xaxis_title="Number of Projects",
            yaxis_title="",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=150, r=40, t=60, b=40),
            height=300,
            font=dict(size=13),
            xaxis=dict(
                gridcolor='rgba(200,200,200,0.3)',
                showgrid=True
            ),
            yaxis=dict(
                tickfont=dict(size=13)
            )
        )
        
        return fig
    
    return go.Figure()

# Callback to update Vetting Status vs Department chart
@app.callback(
    Output("vetting-dept-chart", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_vetting_dept_chart(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    if filtered_df.empty:
        return go.Figure().add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )
    
    # Create Vetting Status vs Department data
    if "Department" in filtered_df.columns and "Vetting status(YES/NO)" in filtered_df.columns:
        vetting_dept = filtered_df.groupby(["Department", "Vetting status(YES/NO)"]).size().reset_index(name="Count")
        
        # Get unique vetting statuses and departments
        vetting_statuses = vetting_dept["Vetting status(YES/NO)"].unique()
        departments = vetting_dept["Department"].unique()
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Define color map for vetting statuses
        color_map = {
            "YES": "#27ae60",
            "NO": "#e74c3c",
            "": "#95a5a6"
        }
        
        for status in vetting_statuses:
            status_data = vetting_dept[vetting_dept["Vetting status(YES/NO)"] == status]
            display_status = status if status else "Not Specified"
            fig.add_trace(go.Bar(
                name=display_status,
                x=status_data["Department"],
                y=status_data["Count"],
                marker_color=color_map.get(status, "#3498db"),
                text=status_data["Count"],
                textposition='auto',
                hovertemplate="<b>%{x}</b><br>Status: " + display_status + "<br>Count: %{y}<extra></extra>"
            ))
        
        fig.update_layout(
            barmode="stack",
            xaxis_title="Department",
            yaxis_title="Number of Projects",
            hovermode="closest",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=9)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=20, t=40, b=100)
        )
        
        return fig
    
    return go.Figure()

# Callback to update Vetting Status vs Zone chart
@app.callback(
    Output("vetting-zone-chart", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_vetting_zone_chart(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    if filtered_df.empty:
        return go.Figure().add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#666")
        )
    
    # Create Vetting Status vs Zone data
    if "Zone" in filtered_df.columns and "Vetting status(YES/NO)" in filtered_df.columns:
        vetting_zone = filtered_df.groupby(["Zone", "Vetting status(YES/NO)"]).size().reset_index(name="Count")
        
        # Get unique vetting statuses and zones
        vetting_statuses = vetting_zone["Vetting status(YES/NO)"].unique()
        zones = vetting_zone["Zone"].unique()
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Define color map for vetting statuses
        color_map = {
            "YES": "#27ae60",
            "NO": "#e74c3c",
            "": "#95a5a6"
        }
        
        for status in vetting_statuses:
            status_data = vetting_zone[vetting_zone["Vetting status(YES/NO)"] == status]
            display_status = status if status else "Not Specified"
            fig.add_trace(go.Bar(
                name=display_status,
                x=status_data["Zone"],
                y=status_data["Count"],
                marker_color=color_map.get(status, "#3498db"),
                text=status_data["Count"],
                textposition='auto',
                hovertemplate="<b>%{x}</b><br>Status: " + display_status + "<br>Count: %{y}<extra></extra>"
            ))
        
        fig.update_layout(
            barmode="stack",
            xaxis_title="Zone",
            yaxis_title="Number of Projects",
            hovermode="closest",
            plot_bgcolor="rgba(240,240,240,0.3)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=10)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=20, t=40, b=100)
        )
        
        return fig
    
    return go.Figure()

# Callback to update Department vs Status graph
@app.callback(
    Output("dept-status-graph", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_dept_status_graph(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    if filtered_df.empty:
        return go.Figure().add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
    
    # Create Department vs Status data
    if "Department" in filtered_df.columns and "Status" in filtered_df.columns:
        dept_status = filtered_df.groupby(["Department", "Status"]).size().reset_index(name="Count")
        
        # Get unique statuses and departments
        statuses = dept_status["Status"].unique()
        departments = dept_status["Department"].unique()
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Define color map for different statuses
        color_map = {
            "Not Initiated": "#e74c3c",
            "Review is pending": "#f39c12",
            "Completed": "#27ae60",
            "dropped": "#95a5a6"
        }
        
        for status in statuses:
            status_data = dept_status[dept_status["Status"] == status]
            fig.add_trace(go.Bar(
                name=status,
                x=status_data["Department"],
                y=status_data["Count"],
                marker_color=color_map.get(status, "#3498db"),
                customdata=status_data[["Department", "Status"]],
                hovertemplate="<b>%{customdata[0]}</b><br>Status: %{customdata[1]}<br>Count: %{y}<extra></extra>"
            ))
        
        fig.update_layout(
            barmode="stack",
            xaxis_title="Department",
            yaxis_title="Number of Projects",
            hovermode="closest",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=10)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=20, t=80, b=120)
        )
        
        return fig
    
    return go.Figure()

# Callback to show department details when clicked
@app.callback(
    Output("department-details", "children"),
    Input("dept-status-graph", "clickData"),
    Input("dept-status-filter-store", "data"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def show_department_details(clickData, dept_status_filter, selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()

    if clickData is None:
        return html.Div([
            html.H5("Department Details", style={"color": "#666", "textAlign": "center", "marginTop": "50px"}),
            html.P("Click on a department in the graph to see details", 
                   style={"textAlign": "center", "color": "#999", "fontSize": "14px"})
        ])
    
    # Get clicked department
    department = clickData["points"][0]["x"]
    
    # Filter data
    filtered_df = df.copy()
    
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    # Filter by selected department
    dept_data = filtered_df[filtered_df["Department"] == department]
    
    if dept_data.empty:
        return html.Div([
            html.H5(f"No data for {department}", style={"color": "#666"})
        ])
    
    # Create summary statistics
    total_projects = len(dept_data)
    status_counts = dept_data["Status"].value_counts().to_dict()
    
    # Build clickable status breakdown buttons
    status_buttons = []
    for status, count in status_counts.items():
        is_active = (dept_status_filter == status)
        btn_style = {
            "fontSize": "11px",
            "marginBottom": "4px",
            "cursor": "pointer",
            "border": "none",
            "background": "#0d6efd" if is_active else "transparent",
            "color": "white" if is_active else "inherit",
            "padding": "4px 8px",
            "borderRadius": "4px",
            "display": "block",
            "width": "100%",
            "textAlign": "left",
        }
        status_buttons.append(
            html.Button(
                [
                    html.Span(f"{status}: ", style={"fontWeight": "600"}),
                    html.Span(f"{count}", style={"color": "white" if is_active else "#0d6efd"})
                ],
                id={"type": "dept-status-filter-btn", "index": status},
                n_clicks=0,
                style=btn_style
            )
        )
    # Add "Show All" button
    show_all_active = (dept_status_filter is None)
    status_buttons.append(
        html.Button(
            "Show All",
            id={"type": "dept-status-filter-btn", "index": "__all__"},
            n_clicks=0,
            style={
                "fontSize": "11px",
                "marginTop": "6px",
                "cursor": "pointer",
                "border": "1px solid #0d6efd",
                "background": "#0d6efd" if show_all_active else "transparent",
                "color": "white" if show_all_active else "#0d6efd",
                "padding": "4px 8px",
                "borderRadius": "4px",
                "display": "block",
                "width": "100%",
                "textAlign": "center",
                "fontWeight": "600",
            }
        )
    )
    
    # Apply status filter to table data
    table_df = dept_data.copy()
    if dept_status_filter and dept_status_filter != "__all__" and "Status" in table_df.columns:
        table_df = table_df[table_df["Status"] == dept_status_filter]
    
    # Prepare data for table - select relevant columns
    display_columns = ["Name", "Project Title", "Status", "Grade", "TARGET DATE"]
    available_columns = [col for col in display_columns if col in table_df.columns]
    
    table_data = table_df[available_columns].fillna("N/A").to_dict("records")
    
    # Filtering indicator
    filter_label = []
    if dept_status_filter and dept_status_filter != "__all__":
        filter_label = [html.Span(f" (Filtered: {dept_status_filter})", style={"fontSize": "11px", "color": "#0d6efd", "fontWeight": "normal"})]
    
    return html.Div([
        html.H4(f"{department}", style={"color": "#0d6efd", "marginBottom": "15px", "fontSize": "18px"}),
        
        # Summary Cards
        html.Div([
            html.Div([
                html.Div("Total Projects", style={"fontSize": "12px", "color": "#666"}),
                html.Div(f"{total_projects}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0d6efd"})
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "10px"}),
            
            html.Div([
                html.Div("Status Breakdown", style={"fontSize": "12px", "color": "#666", "marginBottom": "8px", "fontWeight": "600"}),
                html.Div(status_buttons)
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "15px"})
        ]),
        
        # Data Table
        html.Div([
            html.H5(["Project Details"] + filter_label, style={"fontSize": "14px", "fontWeight": "600", "margin": "0"}),
            html.Button("Download Excel", id={"type": "dept-download-btn", "index": "1"}, n_clicks=0, style={"fontSize": "11px", "padding": "4px 8px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer"})
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "10px"}),
        html.Div([
            dash_table.DataTable(
                id={"type": "dept-project-details-table", "index": "1"},
                data=table_data,
                columns=[{"name": col, "id": col} for col in available_columns],
                style_table={
                    "overflowX": "auto",
                    "overflowY": "auto",
                    "maxHeight": "300px"
                },
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "11px",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                style_header={
                    "backgroundColor": "#0d6efd",
                    "color": "white",
                    "fontWeight": "bold",
                    "fontSize": "12px"
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#f8f9fa"
                    }
                ],
                page_size=10
            )
        ], style={"fontSize": "11px"})
    ])

# Callback for department status filter button clicks
@app.callback(
    Output("dept-status-filter-store", "data"),
    Input({"type": "dept-status-filter-btn", "index": ALL}, "n_clicks"),
    State("dept-status-filter-store", "data"),
    prevent_initial_call=True
)
def dept_status_filter_click(n_clicks_list, current_filter):
    ctx = callback_context
    if not ctx.triggered:
        return current_filter
    
    # Find which button was clicked
    triggered_id = ctx.triggered[0]["prop_id"]
    # Extract the index from the triggered id (format: {"index":"...","type":"..."})
    import json
    try:
        btn_id = json.loads(triggered_id.split(".")[0])
        clicked_status = btn_id["index"]
    except (json.JSONDecodeError, KeyError):
        return current_filter
    
    if clicked_status == "__all__":
        return None
    
    # Toggle: if clicking the same status, deselect it
    if current_filter == clicked_status:
        return None
    
    return clicked_status

# Callback to update Zone vs Status graph
@app.callback(
    Output("zone-status-graph", "figure"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_zone_status_graph(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    if filtered_df.empty:
        return go.Figure().add_annotation(
            text="No data available for the selected filters",
            xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16)
        )
    
    # Create Zone vs Status data
    if "Zone" in filtered_df.columns and "Status" in filtered_df.columns:
        zone_status = filtered_df.groupby(["Zone", "Status"]).size().reset_index(name="Count")
        
        # Get unique statuses and zones
        statuses = zone_status["Status"].unique()
        zones = zone_status["Zone"].unique()
        
        # Create stacked bar chart
        fig = go.Figure()
        
        # Define color map for different statuses
        color_map = {
            "Not Initiated": "#e74c3c",
            "Review is pending": "#f39c12",
            "Completed": "#27ae60",
            "dropped": "#95a5a6"
        }
        
        for status in statuses:
            status_data = zone_status[zone_status["Status"] == status]
            fig.add_trace(go.Bar(
                name=status,
                x=status_data["Zone"],
                y=status_data["Count"],
                marker_color=color_map.get(status, "#3498db"),
                customdata=status_data[["Zone", "Status"]],
                hovertemplate="<b>%{customdata[0]}</b><br>Status: %{customdata[1]}<br>Count: %{y}<extra></extra>"
            ))
        
        fig.update_layout(
            barmode="stack",
            xaxis_title="Zone",
            yaxis_title="Number of Projects",
            hovermode="closest",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font=dict(size=11),
            xaxis=dict(
                tickangle=-45,
                tickfont=dict(size=10)
            ),
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1
            ),
            margin=dict(l=50, r=20, t=80, b=120)
        )
        
        return fig
    
    return go.Figure()

# Callback to show zone details when clicked
@app.callback(
    Output("zone-details", "children"),
    Input("zone-status-graph", "clickData"),
    Input("zone-status-filter-store", "data"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def show_zone_details(clickData, zone_status_filter, selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()

    if clickData is None:
        return html.Div([
            html.H5("Zone Details", style={"color": "#666", "textAlign": "center", "marginTop": "50px"}),
            html.P("Click on a zone in the graph to see details", 
                   style={"textAlign": "center", "color": "#999", "fontSize": "14px"})
        ])
    
    # Get clicked zone
    zone = clickData["points"][0]["x"]
    
    # Filter data
    filtered_df = df.copy()
    
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    # Filter by selected zone
    zone_data = filtered_df[filtered_df["Zone"] == zone]
    
    if zone_data.empty:
        return html.Div([
            html.H5(f"No data for {zone}", style={"color": "#666"})
        ])
    
    # Create summary statistics
    total_projects = len(zone_data)
    status_counts = zone_data["Status"].value_counts().to_dict()
    
    # Build clickable status breakdown buttons
    status_buttons = []
    for status, count in status_counts.items():
        is_active = (zone_status_filter == status)
        btn_style = {
            "fontSize": "11px",
            "marginBottom": "4px",
            "cursor": "pointer",
            "border": "none",
            "background": "#0d6efd" if is_active else "transparent",
            "color": "white" if is_active else "inherit",
            "padding": "4px 8px",
            "borderRadius": "4px",
            "display": "block",
            "width": "100%",
            "textAlign": "left",
        }
        status_buttons.append(
            html.Button(
                [
                    html.Span(f"{status}: ", style={"fontWeight": "600"}),
                    html.Span(f"{count}", style={"color": "white" if is_active else "#0d6efd"})
                ],
                id={"type": "zone-status-filter-btn", "index": status},
                n_clicks=0,
                style=btn_style
            )
        )
    # Add "Show All" button
    show_all_active = (zone_status_filter is None)
    status_buttons.append(
        html.Button(
            "Show All",
            id={"type": "zone-status-filter-btn", "index": "__all__"},
            n_clicks=0,
            style={
                "fontSize": "11px",
                "marginTop": "6px",
                "cursor": "pointer",
                "border": "1px solid #0d6efd",
                "background": "#0d6efd" if show_all_active else "transparent",
                "color": "white" if show_all_active else "#0d6efd",
                "padding": "4px 8px",
                "borderRadius": "4px",
                "display": "block",
                "width": "100%",
                "textAlign": "center",
                "fontWeight": "600",
            }
        )
    )
    
    # Apply status filter to table data
    table_df = zone_data.copy()
    if zone_status_filter and zone_status_filter != "__all__" and "Status" in table_df.columns:
        table_df = table_df[table_df["Status"] == zone_status_filter]
    
    # Prepare data for table - select relevant columns
    display_columns = ["Name", "Department", "Project Title", "Status", "Grade", "TARGET DATE"]
    available_columns = [col for col in display_columns if col in table_df.columns]
    
    table_data = table_df[available_columns].fillna("N/A").to_dict("records")
    
    # Filtering indicator
    filter_label = []
    if zone_status_filter and zone_status_filter != "__all__":
        filter_label = [html.Span(f" (Filtered: {zone_status_filter})", style={"fontSize": "11px", "color": "#0d6efd", "fontWeight": "normal"})]
    
    return html.Div([
        html.H4(f"{zone}", style={"color": "#0d6efd", "marginBottom": "15px", "fontSize": "18px"}),
        
        # Summary Cards
        html.Div([
            html.Div([
                html.Div("Total Projects", style={"fontSize": "12px", "color": "#666"}),
                html.Div(f"{total_projects}", style={"fontSize": "24px", "fontWeight": "bold", "color": "#0d6efd"})
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "10px"}),
            
            html.Div([
                html.Div("Status Breakdown", style={"fontSize": "12px", "color": "#666", "marginBottom": "8px", "fontWeight": "600"}),
                html.Div(status_buttons)
            ], style={"padding": "15px", "backgroundColor": "#f8f9fa", "borderRadius": "8px", "marginBottom": "15px"})
        ]),
        
        # Data Table
        html.Div([
            html.H5(["Project Details"] + filter_label, style={"fontSize": "14px", "fontWeight": "600", "margin": "0"}),
            html.Button("Download Excel", id={"type": "zone-download-btn", "index": "1"}, n_clicks=0, style={"fontSize": "11px", "padding": "4px 8px", "backgroundColor": "#28a745", "color": "white", "border": "none", "borderRadius": "4px", "cursor": "pointer"})
        ], style={"display": "flex", "justifyContent": "space-between", "alignItems": "center", "marginBottom": "10px"}),
        html.Div([
            dash_table.DataTable(
                id={"type": "zone-project-details-table", "index": "1"},
                data=table_data,
                columns=[{"name": col, "id": col} for col in available_columns],
                style_table={
                    "overflowX": "auto",
                    "overflowY": "auto",
                    "maxHeight": "300px"
                },
                style_cell={
                    "textAlign": "left",
                    "padding": "8px",
                    "fontSize": "11px",
                    "whiteSpace": "normal",
                    "height": "auto",
                },
                style_header={
                    "backgroundColor": "#0d6efd",
                    "color": "white",
                    "fontWeight": "bold",
                    "fontSize": "12px"
                },
                style_data_conditional=[
                    {
                        "if": {"row_index": "odd"},
                        "backgroundColor": "#f8f9fa"
                    }
                ],
                page_size=10
            )
        ], style={"fontSize": "11px"})
    ])

# Callback for zone status filter button clicks
@app.callback(
    Output("zone-status-filter-store", "data"),
    Input({"type": "zone-status-filter-btn", "index": ALL}, "n_clicks"),
    State("zone-status-filter-store", "data"),
    prevent_initial_call=True
)
def zone_status_filter_click(n_clicks_list, current_filter):
    ctx = callback_context
    if not ctx.triggered:
        return current_filter
    
    # Find which button was clicked
    triggered_id = ctx.triggered[0]["prop_id"]
    import json
    try:
        btn_id = json.loads(triggered_id.split(".")[0])
        clicked_status = btn_id["index"]
    except (json.JSONDecodeError, KeyError):
        return current_filter
    
    if clicked_status == "__all__":
        return None
    
    # Toggle: if clicking the same status, deselect it
    if current_filter == clicked_status:
        return None
    
    return clicked_status

# Callback to download department details as excel
@app.callback(
    Output("dept-download-excel", "data"),
    Input({"type": "dept-download-btn", "index": ALL}, "n_clicks"),
    State({"type": "dept-project-details-table", "index": ALL}, "data"),
    prevent_initial_call=True
)
def download_dept_excel(n_clicks, table_data):
    if not n_clicks or not n_clicks[0]:
        return dash.no_update
    if table_data and table_data[0]:
        df = pd.DataFrame(table_data[0])
        return dcc.send_data_frame(df.to_excel, "Department_Project_Details.xlsx", index=False)
    return dash.no_update

# Callback to download zone details as excel
@app.callback(
    Output("zone-download-excel", "data"),
    Input({"type": "zone-download-btn", "index": ALL}, "n_clicks"),
    State({"type": "zone-project-details-table", "index": ALL}, "data"),
    prevent_initial_call=True
)
def download_zone_excel(n_clicks, table_data):
    if not n_clicks or not n_clicks[0]:
        return dash.no_update
    if table_data and table_data[0]:
        df = pd.DataFrame(table_data[0])
        return dcc.send_data_frame(df.to_excel, "Zone_Project_Details.xlsx", index=False)
    return dash.no_update

# Callback for project summary
@app.callback(
    Output("project-summary", "children"),
    Input("grade-dropdown", "value"),
    Input("email-dropdown", "value"),
    Input("mobile-dropdown", "value"),
    Input("name-dropdown", "value"),
    Input("eno-dropdown", "value"),
    Input("department-dropdown_NEW", "value"),
    Input("zone-dropdown", "value"),
    Input("project-title-dropdown", "value"),
)
def update_project_summary(selected_grade, selected_email, selected_mobile, selected_name, selected_eno, selected_department, selected_zone, selected_project):
    df = load_fresh_data()
    filtered_df = df.copy()
    
    # Apply filters
    if selected_grade != "All" and "Grade" in df.columns:
        filtered_df = filtered_df[filtered_df["Grade"] == selected_grade]
    
    if selected_email != "All" and "E - Mail" in df.columns:
        filtered_df = filtered_df[filtered_df["E - Mail"] == selected_email]
    
    if selected_mobile != "All" and "Mobile No." in df.columns:
        filtered_df = filtered_df[filtered_df["Mobile No."] == selected_mobile]
    
    if selected_name != "All" and "Name" in df.columns:
        filtered_df = filtered_df[filtered_df["Name"] == selected_name]
    
    if selected_eno != "All" and "E.No." in df.columns:
        filtered_df = filtered_df[filtered_df["E.No."] == selected_eno]
    
    if selected_department != "All" and "Department" in df.columns:
        filtered_df = filtered_df[filtered_df["Department"] == selected_department]
    
    if selected_zone != "All" and "Zone" in df.columns:
        filtered_df = filtered_df[filtered_df["Zone"] == selected_zone]
    
    if selected_project != "All" and "Project Title" in df.columns:
        filtered_df = filtered_df[filtered_df["Project Title"] == selected_project]
    
    if filtered_df.empty:
        return dbc.Alert("No project data found for the selected filters.", color="warning")
    
    # Display summary information
    return html.Div([
        html.H4(f"Overall Summary: {len(filtered_df)} project(s)", style={"marginBottom": "15px"}),
        html.Div(f"Filters applied: Grade={selected_grade}, Email={selected_email}, Mobile={selected_mobile}, Name={selected_name}, E.No.={selected_eno}, Department={selected_department}, Zone={selected_zone}, Project={selected_project}", 
                 style={"fontSize": "14px", "marginBottom": "10px", "color": "#666"})
    ])