import os
import csv
import uuid
import base64
from datetime import datetime

import dash
from dash import html, dcc, Input, Output, State, ctx, MATCH, ALL
import dash_bootstrap_components as dbc
import pandas as pd
import plotly.express as px

# Page registration
dash.register_page(__name__, path="/solid-waste-management")

SWM_CSV = "./Data/solid_waste_management.csv"
SWM_IMG_DIR = "./assets/K5/solid_waste_images"

DEPARTMENTS = [
    'RMHS', 'PP- & OBP-1', 'PP-2', 'PP-3', 'SP1', 'SP-2,3, 4 &5', 'LCP-1 TO 4',
    'CO-3&4', 'CO-5', 'CX-1&2', 'BF-1&2', 'BF-4', 'BF-5', 'DRI', 'SMS-1',
    'SMS-2', 'SMS-3', 'SMS-4', 'HSM-1', 'HSM-2', 'HSM-3', 'WRM-1 & BRM-1',
    'WRM-2 & BRM-2', 'CRM-1', 'CRM-2', 'EMD', 'UTILITY', 'CMD/ISHOP/MRS',
    'LOGISTIC'
]

def load_swm_data():
    if not os.path.exists(SWM_CSV):
        return pd.DataFrame(columns=['S #', 'PRODUCT', 'PRODUCT DESCRIPTION', 'Examples', 'photo', 'UOM'] + DEPARTMENTS + ['Total (months)', 'Total (per year)'])
    try:
        df = pd.read_csv(SWM_CSV)
        # Normalize column names: remove newlines, double spaces, and strip them
        df.columns = [' '.join(c.split()) for c in df.columns]
        
        # Coerce department columns to numeric
        for dept in DEPARTMENTS:
            if dept in df.columns:
                df[dept] = pd.to_numeric(df[dept], errors='coerce').fillna(0.0)
            else:
                df[dept] = 0.0
                
        # Coerce numeric columns
        df['S #'] = pd.to_numeric(df['S #'], errors='coerce').fillna(0.0)
        df['PRODUCT'] = df['PRODUCT'].astype(str).str.strip()
        df['PRODUCT DESCRIPTION'] = df['PRODUCT DESCRIPTION'].fillna('').astype(str).str.strip()
        df['Examples'] = df['Examples'].fillna('').astype(str).str.strip()
        df['photo'] = df['photo'].fillna('').astype(str).str.strip()
        df['UOM'] = df['UOM'].fillna('MT').astype(str).str.strip()
        df['Total (months)'] = pd.to_numeric(df['Total (months)'], errors='coerce').fillna(0.0)
        df['Total (per year)'] = pd.to_numeric(df['Total (per year)'], errors='coerce').fillna(0.0)
        return df
    except Exception as e:
        print("Error loading SWM data:", e)
        return pd.DataFrame(columns=['S #', 'PRODUCT', 'PRODUCT DESCRIPTION', 'Examples', 'photo', 'UOM'] + DEPARTMENTS + ['Total (months)', 'Total (per year)'])

def save_swm_data(df):
    try:
        os.makedirs(os.path.dirname(SWM_CSV), exist_ok=True)
        df.to_csv(SWM_CSV, index=False)
        return True
    except Exception as e:
        print("Error saving SWM data:", e)
        return False

def build_product_card(row, selected_dept=None):
    product_code = row['PRODUCT']
    desc = row['PRODUCT DESCRIPTION']
    examples = row.get('Examples', '')
    photo = row.get('photo', '')
    uom = row.get('UOM', 'MT')
    monthly_total = row.get('Total (months)', 0.0)
    yearly_total = row.get('Total (per year)', 0.0)
    
    # Image or placeholder
    if photo and str(photo).strip() != 'nan' and str(photo).strip() != '':
        img_src = f"/assets/K5/solid_waste_images/{photo}"
        img_element = html.Img(src=img_src, style={"height": "180px", "width": "100%", "objectFit": "cover"})
    else:
        # Beautiful gradient placeholder
        img_element = html.Div([
            html.I(className="bi bi-trash3", style={"fontSize": "40px", "color": "rgba(255,255,255,0.7)"}),
            html.Div(desc[:20] + "..." if len(desc) > 20 else desc, className="mt-2 text-uppercase fw-bold text-center px-2", style={"fontSize": "11px", "letterSpacing": "1px", "color": "rgba(255,255,255,0.9)"})
        ], className="swm-placeholder-img")
        
    # Build department breakdown content
    dept_rows = []
    for dept in DEPARTMENTS:
        qty = row.get(dept, 0.0)
        if qty > 0.0:
            is_active = (dept == selected_dept)
            dept_rows.append(html.Div([
                html.Span(dept, className="fw-bold" if is_active else "", style={"color": "#1e3d59" if is_active else "#555"}),
                html.Span(f"{qty:.3f} {uom}", className=f"badge {'bg-primary' if is_active else 'bg-light text-dark'} float-end")
            ], className="py-1 border-bottom d-flex justify-content-between align-items-center", style={"fontSize": "13px"}))
            
    if not dept_rows:
        dept_rows.append(html.Div("No department generation recorded.", className="text-muted small text-center py-2"))
        
    # Department breakdown collapse
    breakdown_section = html.Div([
        dbc.Button("🏢 Department Breakdown", id={"type": "swm-new-collapse-btn", "index": product_code}, color="secondary", outline=True, size="sm", className="w-100 mt-3 swm-collapse-btn"),
        dbc.Collapse(
            html.Div(dept_rows, className="mt-2 p-2 border rounded bg-light", style={"maxHeight": "200px", "overflowY": "auto"}),
            id={"type": "swm-new-collapse", "index": product_code},
            is_open=False
        )
    ])
    
    # Selected dept highlight badge
    highlight_badge = None
    if selected_dept and row.get(selected_dept, 0.0) > 0.0:
        highlight_badge = dbc.Badge(f"{selected_dept}: {row[selected_dept]:.3f} {uom}", color="primary", className="position-absolute top-0 end-0 m-2 px-2 py-1 shadow-sm")
        
    return dbc.Col([
        dbc.Card([
            html.Div([
                img_element,
                highlight_badge
            ], style={"position": "relative", "overflow": "hidden"}),
            dbc.CardBody([
                html.Div(f"CODE: {product_code}", className="text-muted small fw-bold mb-1"),
                html.H6(desc, className="fw-bold mb-2 text-dark text-truncate-2", title=desc, style={"height": "40px", "lineHeight": "20px", "overflow": "hidden"}),
                
                # UOM Badge & Quantities
                html.Div([
                    dbc.Badge(uom, color="info", className="me-2 px-2 py-1"),
                    html.Span("Monthly: ", className="text-muted small"),
                    html.Span(f"{monthly_total:.2f}", className="fw-bold text-dark small me-3"),
                    html.Span("Yearly: ", className="text-muted small"),
                    html.Span(f"{yearly_total:.2f}", className="fw-bold text-dark small")
                ], className="d-flex align-items-center mb-2"),
                
                # Examples
                html.Div([
                    html.Span("Examples: ", className="fw-bold small text-muted"),
                    html.Span(examples if examples else "None specified", className="small text-muted italic")
                ], className="text-truncate", title=examples if examples else None, style={"fontSize": "12px", "minHeight": "18px"}),
                
                breakdown_section
            ], className="p-3")
        ], className="swm-card h-100 border-0 shadow-sm")
    ], lg=4, md=6, sm=12, className="mb-4")

# Layout
layout = dbc.Container([
    # Stores for pagination and reload triggers
    dcc.Store(id="swm-new-page-store", data=0),
    dcc.Store(id="swm-new-total-pages-store", data=1),
    dcc.Store(id="swm-new-reload-trigger", data=0),
    
    # Page Header
    dbc.Row([
        dbc.Col([
            html.H3("Solid Waste Management Dashboard", className="fw-bold mb-1", style={"color": "#1e3d59"}),
            html.P("Comprehensive product-wise tracking of solid waste generation across all departments", className="text-muted small"),
        ], md=8),
        dbc.Col([
            dbc.Button("➕ Add New Product", id="swm-new-toggle-form-btn", color="primary", className="float-end shadow-sm fw-bold px-3 py-2", style={"borderRadius": "10px"}),
        ], md=4, className="d-flex align-items-center justify-content-end")
    ], className="mb-4 pt-3"),
    
    # Collapsible Add New Product Form
    dbc.Collapse([
        dbc.Card([
            dbc.CardHeader([
                html.H6("➕ Add New Product to Database", className="mb-0 fw-bold", style={"color": "#1e3d59"}),
            ], className="bg-transparent border-0 pt-3 px-4"),
            dbc.CardBody([
                dbc.Row([
                    dbc.Col([
                        html.Label("Product Code (PRODUCT)", className="fw-bold text-muted small mb-1"),
                        dbc.Input(id="new-prod-code", type="text", placeholder="e.g. 7100002507", style={"borderRadius": "8px"}),
                    ], md=2, sm=6, className="mb-2"),
                    dbc.Col([
                        html.Label("Product Description", className="fw-bold text-muted small mb-1"),
                        dbc.Input(id="new-prod-desc", type="text", placeholder="e.g. SCRAPPED STEEL DRUMS", style={"borderRadius": "8px"}),
                    ], md=4, sm=6, className="mb-2"),
                    dbc.Col([
                        html.Label("UOM", className="fw-bold text-muted small mb-1"),
                        dcc.Dropdown(
                            id="new-prod-uom",
                            options=[
                                {"label": "MT (Metric Ton)", "value": "MT"},
                                {"label": "EA (Each)", "value": "EA"},
                                {"label": "DR (Drum)", "value": "DR"},
                                {"label": "LTR (Litre)", "value": "LTR"},
                                {"label": "SET", "value": "SET"},
                            ],
                            placeholder="Select UOM",
                            clearable=False,
                            style={"borderRadius": "8px"}
                        )
                    ], md=2, sm=4, className="mb-2"),
                    dbc.Col([
                        html.Label("Department", className="fw-bold text-muted small mb-1"),
                        dcc.Dropdown(
                            id="new-prod-dept",
                            options=[{"label": dept, "value": dept} for dept in DEPARTMENTS],
                            placeholder="Select Dept",
                            clearable=False,
                            style={"borderRadius": "8px"}
                        )
                    ], md=2, sm=4, className="mb-2"),
                    dbc.Col([
                        html.Label("Qty (Monthly)", className="fw-bold text-muted small mb-1"),
                        dbc.Input(id="new-prod-qty", type="number", min=0, value=0.0, step=0.001, style={"borderRadius": "8px"}),
                    ], md=2, sm=4, className="mb-2"),
                ]),
                dbc.Row([
                    dbc.Col([
                        html.Label("Examples", className="fw-bold text-muted small mb-1"),
                        dbc.Input(id="new-prod-examples", type="text", placeholder="e.g. empty bins, damaged containers", style={"borderRadius": "8px"}),
                    ], md=6, className="mb-2"),
                    dbc.Col([
                        html.Label("Upload Photo", className="fw-bold text-muted small mb-1"),
                        dcc.Upload(
                            id="new-prod-upload-photo",
                            children=html.Div(["Drag & Drop or ", html.A("Select Image", href="#", className="text-decoration-none fw-bold")]),
                            style={
                                "height": "38px",
                                "lineHeight": "38px",
                                "borderWidth": "1px",
                                "borderStyle": "dashed",
                                "borderRadius": "8px",
                                "textAlign": "center",
                                "cursor": "pointer",
                                "background": "#f8f9fa",
                                "borderColor": "#ced4da"
                            },
                            multiple=False
                        ),
                        html.Div(id="swm-new-upload-status", className="small text-muted mt-1 px-1")
                    ], md=4, className="mb-2"),
                    dbc.Col([
                        dbc.Button("Add Product", id="new-prod-add-btn", color="primary", className="w-100 shadow-sm fw-bold", style={"height": "38px", "borderRadius": "8px", "marginTop": "22px"}),
                    ], md=2, className="mb-2")
                ]),
                html.Div(id="new-prod-alert-msg", className="mt-3")
            ], className="px-4 pb-4")
        ], className="border-0 shadow-sm mb-4", style={"borderRadius": "16px"})
    ], id="swm-new-add-form-collapse", is_open=False),
    
    # KPI Stats Cards Overview
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div("Total Products", className="kpi-title"),
                            html.Div(id="swm-new-kpi-total-products", className="kpi-value")
                        ], xs=8),
                        dbc.Col([
                            html.Div(
                                html.I(className="bi bi-box-seam", style={"fontSize": "20px", "color": "#0d6efd"}),
                                className="kpi-icon-container", style={"backgroundColor": "#e7f1ff"}
                            )
                        ], xs=4, className="d-flex align-items-center justify-content-end")
                    ])
                ])
            ], className="kpi-card mb-3")
        ], lg=4, md=6, sm=12),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div("Total Generation (MT/Mo)", className="kpi-title"),
                            html.Div(id="swm-new-kpi-total-mt", className="kpi-value")
                        ], xs=8),
                        dbc.Col([
                            html.Div(
                                html.I(className="bi bi-speedometer2", style={"fontSize": "20px", "color": "#17b978"}),
                                className="kpi-icon-container", style={"backgroundColor": "#e8faf0"}
                            )
                        ], xs=4, className="d-flex align-items-center justify-content-end")
                    ])
                ])
            ], className="kpi-card mb-3")
        ], lg=4, md=6, sm=12),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dbc.Row([
                        dbc.Col([
                            html.Div("Top Generating Dept", className="kpi-title"),
                            html.Div(id="swm-new-kpi-top-dept", className="kpi-value", style={"fontSize": "18px", "marginTop": "6px"})
                        ], xs=8),
                        dbc.Col([
                            html.Div(
                                html.I(className="bi bi-building", style={"fontSize": "20px", "color": "#ffc107"}),
                                className="kpi-icon-container", style={"backgroundColor": "#fffbeb"}
                            )
                        ], xs=4, className="d-flex align-items-center justify-content-end")
                    ])
                ])
            ], className="kpi-card mb-3")
        ], lg=4, md=12, sm=12)
    ], className="mb-4"),
    
    # Analytical Charts Panel
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="swm-new-dept-chart", config={"displayModeBar": False})
                ])
            ], className="border-0 shadow-sm mb-4", style={"borderRadius": "16px"})
        ], md=6),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    dcc.Graph(id="swm-new-uom-chart", config={"displayModeBar": False})
                ])
            ], className="border-0 shadow-sm mb-4", style={"borderRadius": "16px"})
        ], md=6)
    ]),
    
    # Search and Filter Toolbar Card
    dbc.Card([
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    html.Label("Search Product", className="fw-bold text-muted small mb-1"),
                    dbc.Input(id="swm-new-search-input", placeholder="Search by name or code...", type="text", style={"borderRadius": "8px"}),
                ], lg=4, md=6, sm=12, className="mb-2"),
                dbc.Col([
                    html.Label("Filter by Department", className="fw-bold text-muted small mb-1"),
                    dcc.Dropdown(
                        id="swm-new-dept-filter",
                        options=[{"label": dept, "value": dept} for dept in DEPARTMENTS],
                        placeholder="All Departments",
                        clearable=True,
                        style={"borderRadius": "8px"}
                    ),
                ], lg=3, md=6, sm=12, className="mb-2"),
                dbc.Col([
                    html.Label("Filter by UOM", className="fw-bold text-muted small mb-1"),
                    dcc.Dropdown(
                        id="swm-new-uom-filter",
                        options=[
                            {"label": "MT", "value": "MT"},
                            {"label": "EA / EACH", "value": "EA"},
                            {"label": "DR", "value": "DR"},
                            {"label": "LTR", "value": "LTR"},
                            {"label": "SET", "value": "SET"},
                        ],
                        placeholder="All UOMs",
                        clearable=True,
                        style={"borderRadius": "8px"}
                    ),
                ], lg=2, md=4, sm=6, className="mb-2"),
                dbc.Col([
                    html.Label("Sort By", className="fw-bold text-muted small mb-1"),
                    dcc.Dropdown(
                        id="swm-new-sort-by",
                        options=[
                            {"label": "Highest Monthly Gen", "value": "monthly_desc"},
                            {"label": "Lowest Monthly Gen", "value": "monthly_asc"},
                            {"label": "Highest Yearly Gen", "value": "yearly_desc"},
                            {"label": "Product Code (0-9)", "value": "code_asc"},
                            {"label": "Product Name (A-Z)", "value": "name_asc"},
                        ],
                        value="monthly_desc",
                        clearable=False,
                        style={"borderRadius": "8px"}
                    ),
                ], lg=2, md=4, sm=6, className="mb-2"),
                dbc.Col([
                    dbc.Button("Reset", id="swm-new-reset-btn", color="light", className="w-100 fw-bold border text-muted", style={"borderRadius": "8px", "height": "38px", "marginTop": "22px"}),
                ], lg=1, md=4, sm=12, className="mb-2")
            ])
        ], className="p-3")
    ], className="border-0 shadow-sm mb-4", style={"borderRadius": "16px", "backgroundColor": "rgba(255, 255, 255, 0.9)"}),
    
    # Product Cards Grid
    dbc.Row(id="swm-new-cards-grid", className="mb-3"),
    
    # Pagination
    html.Div([
        dbc.Button("◀ Previous", id="swm-new-prev-btn", color="primary", outline=True, size="sm", style={"borderRadius": "8px"}),
        html.Span(id="swm-new-page-indicator", className="align-self-center mx-3 fw-bold text-muted", style={"fontSize": "14px"}),
        dbc.Button("Next ▶", id="swm-new-next-btn", color="primary", outline=True, size="sm", style={"borderRadius": "8px"}),
    ], className="d-flex justify-content-center mt-3 mb-5")
], fluid=True, style={"backgroundColor": "#f4f7fc", "minHeight": "100vh"})


# -------------------------------------------------------------
# Callbacks
# -------------------------------------------------------------

# Toggle collapsible Add Product Form
@dash.callback(
    Output("swm-new-add-form-collapse", "is_open"),
    Output("swm-new-toggle-form-btn", "children"),
    Input("swm-new-toggle-form-btn", "n_clicks"),
    State("swm-new-add-form-collapse", "is_open"),
    prevent_initial_call=True
)
def swm_new_toggle_form(n_clicks, is_open):
    if is_open:
        return False, "➕ Add New Product"
    return True, "➖ Hide Form"


# Photo upload status display
@dash.callback(
    Output("swm-new-upload-status", "children"),
    Input("new-prod-upload-photo", "contents"),
    State("new-prod-upload-photo", "filename"),
    prevent_initial_call=True
)
def swm_new_upload_status(contents, filename):
    if not contents:
        return ""
    return f"📸 Selected: {filename}"


# Reset search and filters
@dash.callback(
    Output("swm-new-search-input", "value"),
    Output("swm-new-dept-filter", "value"),
    Output("swm-new-uom-filter", "value"),
    Output("swm-new-sort-by", "value"),
    Input("swm-new-reset-btn", "n_clicks"),
    prevent_initial_call=True
)
def swm_new_reset_filters(n_clicks):
    return "", None, None, "monthly_desc"


# Handle page store logic based on filters and buttons
@dash.callback(
    Output("swm-new-page-store", "data"),
    Input("swm-new-prev-btn", "n_clicks"),
    Input("swm-new-next-btn", "n_clicks"),
    Input("swm-new-search-input", "value"),
    Input("swm-new-dept-filter", "value"),
    Input("swm-new-uom-filter", "value"),
    Input("swm-new-sort-by", "value"),
    Input("swm-new-reset-btn", "n_clicks"),
    State("swm-new-page-store", "data"),
    State("swm-new-total-pages-store", "data")
)
def swm_new_handle_page_state(prev, next_btn, search, dept, uom, sort, reset, current_page, total_pages):
    triggered = ctx.triggered_id
    if not triggered:
        return 0
        
    # Reset page to 0 if filters change
    if triggered in ["swm-new-search-input", "swm-new-dept-filter", "swm-new-uom-filter", "swm-new-sort-by", "swm-new-reset-btn"]:
        return 0
        
    # Handle pagination clicks
    current_page = current_page or 0
    if triggered == "swm-new-prev-btn":
        return max(0, current_page - 1)
    if triggered == "swm-new-next-btn":
        total = total_pages or 1
        return min(total - 1, current_page + 1)
        
    return 0


# Add a complete new product
@dash.callback(
    Output("new-prod-alert-msg", "children"),
    Output("swm-new-reload-trigger", "data"),
    Output("new-prod-code", "value"),
    Output("new-prod-desc", "value"),
    Output("new-prod-uom", "value"),
    Output("new-prod-dept", "value"),
    Output("new-prod-qty", "value"),
    Output("new-prod-examples", "value"),
    Output("new-prod-upload-photo", "contents"),
    Output("swm-new-upload-status", "children", allow_duplicate=True),
    Input("new-prod-add-btn", "n_clicks"),
    State("new-prod-code", "value"),
    State("new-prod-desc", "value"),
    State("new-prod-uom", "value"),
    State("new-prod-dept", "value"),
    State("new-prod-qty", "value"),
    State("new-prod-examples", "value"),
    State("new-prod-upload-photo", "contents"),
    State("new-prod-upload-photo", "filename"),
    State("swm-new-reload-trigger", "data"),
    prevent_initial_call=True
)
def swm_new_add_product(n_clicks, code, desc, uom, dept, qty, examples, photo_contents, photo_filename, reload_val):
    if not n_clicks:
        raise dash.exceptions.PreventUpdate
        
    # Validate fields
    if not code or not str(code).strip():
        return dbc.Alert("Product Code is required.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update
    if not desc or not str(desc).strip():
        return dbc.Alert("Product Description is required.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update
    if not uom:
        return dbc.Alert("Please select a UOM.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update
    if not dept:
        return dbc.Alert("Please select a Department.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update
        
    qty = float(qty or 0.0)
    
    # Load database
    df = load_swm_data()
    
    # Validate uniqueness of product code
    code_str = str(code).strip()
    if code_str in df['PRODUCT'].astype(str).values:
        return dbc.Alert(f"Product Code '{code_str}' already exists in the database.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update
        
    # Handle photo upload
    photo_name = ""
    if photo_contents:
        try:
            os.makedirs(SWM_IMG_DIR, exist_ok=True)
            header, encoded = photo_contents.split(",", 1)
            image_bytes = base64.b64decode(encoded)
            _, ext = os.path.splitext(photo_filename or "")
            if not ext:
                ext = ".jpg"
            photo_name = f"swm_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}{ext}"
            image_path = os.path.join(SWM_IMG_DIR, photo_name)
            with open(image_path, "wb") as f:
                f.write(image_bytes)
        except Exception as e:
            return dbc.Alert(f"Failed to save uploaded image: {e}", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update

    # Create new row dict
    new_row = {
        'S #': len(df) + 1,
        'PRODUCT': code_str,
        'PRODUCT DESCRIPTION': str(desc).strip(),
        'Examples': str(examples or '').strip(),
        'photo': photo_name,
        'UOM': uom,
        'Total (months)': qty,
        'Total (per year)': qty * 12.0
    }
    
    # Set all departments
    for d in DEPARTMENTS:
        new_row[d] = qty if d == dept else 0.0
        
    # Append and save
    df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
    if save_swm_data(df):
        alert = dbc.Alert(f"Product '{desc}' added successfully!", color="success", dismissable=True)
        return alert, (reload_val or 0) + 1, "", "", None, None, 0.0, "", None, ""
    else:
        return dbc.Alert("Failed to save product to database. Check server logs.", color="danger", dismissable=True), reload_val, code, desc, uom, dept, qty, examples, photo_contents, dash.no_update


# Main callback to render stats, charts, and product grid
@dash.callback(
    Output("swm-new-cards-grid", "children"),
    Output("swm-new-page-indicator", "children"),
    Output("swm-new-total-pages-store", "data"),
    Output("swm-new-kpi-total-products", "children"),
    Output("swm-new-kpi-total-mt", "children"),
    Output("swm-new-kpi-top-dept", "children"),
    Output("swm-new-dept-chart", "figure"),
    Output("swm-new-uom-chart", "figure"),
    Input("swm-new-page-store", "data"),
    Input("swm-new-search-input", "value"),
    Input("swm-new-dept-filter", "value"),
    Input("swm-new-uom-filter", "value"),
    Input("swm-new-sort-by", "value"),
    Input("swm-new-reload-trigger", "data")
)
def swm_new_render_dashboard(page_num, search, dept_filter, uom_filter, sort_by, reload_trig):
    # Load data
    df = load_swm_data()
    
    if df.empty:
        empty_fig = px.bar(title="No Data Available")
        return html.Div("No products found in database.", className="text-center w-100 my-5"), "Page 1 of 1", 1, "0", "0.00 MT", "N/A", empty_fig, empty_fig

    # 1. Filter data
    filtered_df = df.copy()
    if search:
        s = str(search).lower().strip()
        filtered_df = filtered_df[
            filtered_df['PRODUCT'].astype(str).str.lower().str.contains(s) |
            filtered_df['PRODUCT DESCRIPTION'].astype(str).str.lower().str.contains(s)
        ]
        
    if dept_filter:
        filtered_df = filtered_df[filtered_df[dept_filter] > 0.0]
        
    if uom_filter:
        filtered_df = filtered_df[filtered_df['UOM'] == uom_filter]
        
    # 2. Sort data
    if sort_by == "monthly_desc":
        filtered_df = filtered_df.sort_values(by="Total (months)", ascending=False)
    elif sort_by == "monthly_asc":
        filtered_df = filtered_df.sort_values(by="Total (months)", ascending=True)
    elif sort_by == "yearly_desc":
        filtered_df = filtered_df.sort_values(by="Total (per year)", ascending=False)
    elif sort_by == "code_asc":
        filtered_df = filtered_df.sort_values(by="PRODUCT", ascending=True)
    elif sort_by == "name_asc":
        filtered_df = filtered_df.sort_values(by="PRODUCT DESCRIPTION", ascending=True)

    # 3. Calculate metrics
    total_products = len(filtered_df)
    
    # Total monthly MT (only sum for products where UOM is MT)
    mt_df = filtered_df[filtered_df['UOM'] == 'MT']
    total_mt = mt_df['Total (months)'].sum() if not mt_df.empty else 0.0
    
    # Top Generating Department (sum all department columns in filtered data)
    dept_sums = {}
    for d in DEPARTMENTS:
        dept_sums[d] = filtered_df[d].sum()
        
    top_dept_name = "N/A"
    top_dept_val = 0.0
    if dept_sums and sum(dept_sums.values()) > 0.0:
        top_dept_name = max(dept_sums, key=dept_sums.get)
        top_dept_val = dept_sums[top_dept_name]
        
    kpi_top_dept_text = f"{top_dept_name} ({top_dept_val:.1f})" if top_dept_name != "N/A" else "N/A"

    # 4. Generate plots
    # Horizontal bar chart of top generating departments
    bar_data = pd.DataFrame(list(dept_sums.items()), columns=['Department', 'Quantity'])
    bar_data = bar_data.sort_values(by='Quantity', ascending=False).head(10)
    
    dept_fig = px.bar(
        bar_data, 
        x='Quantity', 
        y='Department', 
        orientation='h',
        title='Top 10 Generating Departments (Monthly Total)',
        color='Quantity',
        color_continuous_scale=px.colors.sequential.Viridis,
        labels={'Quantity': 'Qty (Monthly Units)', 'Department': 'Department'}
    )
    dept_fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        xaxis=dict(showgrid=True, gridcolor='#eef2f6'),
        yaxis=dict(autorange='reversed'),
        coloraxis_showscale=False,
        height=300,
        font=dict(size=11, family="Inter, sans-serif")
    )
    
    # Pie chart of UOM distribution
    uom_counts = filtered_df['UOM'].value_counts().reset_index()
    uom_counts.columns = ['UOM', 'Count']
    
    uom_fig = px.pie(
        uom_counts, 
        values='Count', 
        names='UOM', 
        title='Products Count by Unit of Measure (UOM)',
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    uom_fig.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        height=300,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        font=dict(size=11, family="Inter, sans-serif")
    )

    # 5. Paginate card grid
    PAGE_SIZE = 12
    page_num = page_num or 0
    total_pages = max(1, (total_products + PAGE_SIZE - 1) // PAGE_SIZE)
    
    # Ensure current page is inside bounds
    if page_num >= total_pages:
        page_num = total_pages - 1
    page_num = max(0, page_num)
    
    start_idx = page_num * PAGE_SIZE
    end_idx = start_idx + PAGE_SIZE
    sliced_df = filtered_df.iloc[start_idx:end_idx]
    
    card_elements = []
    if sliced_df.empty:
        card_elements = [html.Div("No products match the selected filters.", className="text-center text-muted my-5 w-100")]
    else:
        for _, row in sliced_df.iterrows():
            card_elements.append(build_product_card(row, dept_filter))
            
    page_indicator = f"Page {page_num + 1} of {total_pages}"
    
    return (
        card_elements,
        page_indicator,
        total_pages,
        str(total_products),
        f"{total_mt:.2f} MT",
        kpi_top_dept_text,
        dept_fig,
        uom_fig
    )


# Pattern matching callback to toggle collapse on cards
@dash.callback(
    Output({"type": "swm-new-collapse", "index": MATCH}, "is_open"),
    Input({"type": "swm-new-collapse-btn", "index": MATCH}, "n_clicks"),
    State({"type": "swm-new-collapse", "index": MATCH}, "is_open"),
    prevent_initial_call=True
)
def swm_new_toggle_card_collapse(n_clicks, is_open):
    if n_clicks:
        return not is_open
    return is_open
