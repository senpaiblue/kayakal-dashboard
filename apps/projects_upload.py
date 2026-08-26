import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from server import app
import pandas as pd
import base64
import io
import os
from pathlib import Path

CSV_PATH = os.path.abspath("./Data/projects_data.csv")

def save_csv_safely(df, path):
    """Save CSV with proper flushing to disk - critical for server deployments"""
    # Save to CSV
    df.to_csv(path, index=False, encoding='utf-8')
    
    # Force flush to disk
    try:
        # Sync file system to ensure data is written (Unix/Linux)
        if hasattr(os, 'sync'):
            os.sync()
    except:
        pass
    
    # Additional verification - read file size to ensure it's written
    try:
        file_size = os.path.getsize(path)
        if file_size == 0:
            raise IOError(f"CSV file {path} was written but has zero size")
    except Exception as e:
        print(f"Warning: Could not verify CSV write: {e}")

layout = html.Div([
    html.H2("Projects Data Management", style={"marginBottom": "30px", "color": "#0d6efd"}),
    
    # Tabs for different operations
    dbc.Tabs([
        # Tab 1: Add New Individual
        dbc.Tab(label="Add New Individual", tab_id="add-new", children=[
            html.Div([
                html.H4("Add New Individual to Database", style={"marginTop": "20px", "marginBottom": "20px", "color": "#333"}),
                html.Div(id="add-new-form-container"),
                html.Br(),
                dbc.Button("Add to Database", id="btn-add-new", color="success", size="lg", className="me-2"),
                html.Div(id="add-new-output", style={"marginTop": "20px"})
            ], style={"padding": "20px"})
        ]),
        
        # Tab 2: Edit Existing Individual
        dbc.Tab(label="Edit Existing Individual", tab_id="edit-existing", children=[
            html.Div([
                html.H4("Edit Existing Individual", style={"marginTop": "20px", "marginBottom": "20px", "color": "#333"}),
                html.P("Enter Employee Number to search:", style={"fontSize": "16px", "color": "#666"}),
                dbc.InputGroup([
                    dbc.Input(id="search-eno", placeholder="Enter Employee No. (E.No.)", type="text"),
                    dbc.Button("Search", id="btn-search-eno", color="primary")
                ], style={"marginBottom": "20px", "maxWidth": "500px"}),
                html.Div(id="edit-form-output"),
                html.Div(id="edit-form-container", style={"display": "none"}),
                html.Div(id="edit-save-output", style={"marginTop": "20px"})
            ], style={"padding": "20px"})
        ]),
        
        # Tab 3: Upload File
        dbc.Tab(label="Upload Excel File", tab_id="upload-file", children=[
            html.Div([
                html.Div([
                    html.Small("Expected column headers:", style={"fontWeight": "600", "color": "#666", "marginTop": "20px", "display": "block"}),
                    html.Div(id="expected-columns-display", style={"fontSize": "11px", "color": "#999", "marginBottom": "15px"})
                ]),
                
                html.P("Upload a new Excel file (.xlsx) to add data to the projects database.", 
                       style={"fontSize": "16px", "color": "#666", "marginBottom": "10px"}),
                html.P("Note: Column headers must exactly match the existing data. Only matching columns will be saved.", 
                       style={"fontSize": "14px", "color": "#e74c3c", "marginBottom": "5px", "fontStyle": "italic", "fontWeight": "600"}),
                html.P("Smart Update: If Employee No. + Project Title combination exists, that row will be UPDATED. Otherwise, it will be ADDED as new.", 
                       style={"fontSize": "14px", "color": "#27ae60", "marginBottom": "20px", "fontStyle": "italic", "fontWeight": "600"}),
                
                dcc.Upload(
                    id='upload-projects-data',
                    children=html.Div([
                        html.I(className="fas fa-cloud-upload-alt", style={"fontSize": "48px", "color": "#0d6efd", "marginBottom": "15px"}),
                        html.P('Drag and Drop or Click to Select Excel File (.xlsx)', 
                               style={"fontSize": "16px", "margin": "0"})
                    ]),
                    style={
                        'width': '100%',
                        'height': '200px',
                        'lineHeight': '200px',
                        'borderWidth': '2px',
                        'borderStyle': 'dashed',
                        'borderRadius': '10px',
                        'borderColor': '#0d6efd',
                        'textAlign': 'center',
                        'backgroundColor': '#f8f9fa',
                        'cursor': 'pointer',
                        'display': 'flex',
                        'flexDirection': 'column',
                        'alignItems': 'center',
                        'justifyContent': 'center',
                        'lineHeight': 'normal'
                    },
                    multiple=False,
                    accept=".xls,.xlsx"
                ),
                
                html.Div(id='upload-projects-output', style={"marginTop": "20px"}),
                
                html.Hr(style={"margin": "40px 0"}),
                
                html.H4("Current Data Preview (All Records)", style={"marginBottom": "20px", "color": "#333"}),
                html.Div(id='current-projects-preview')
                
            ], style={"padding": "20px", "maxWidth": "1200px"})
        ]),
        
        # Tab 4: Delete Individual
        dbc.Tab(label="Delete Individual", tab_id="delete-individual", children=[
            html.Div([
                html.H4("Delete Individual from Database", style={"marginTop": "20px", "marginBottom": "20px", "color": "#333"}),
                html.P("Enter Employee Number to search and delete:", style={"fontSize": "16px", "color": "#666"}),
                dbc.InputGroup([
                    dbc.Input(id="delete-search-eno", placeholder="Enter Employee No. (E.No.)", type="text"),
                    dbc.Button("Search", id="btn-delete-search-eno", color="primary")
                ], style={"marginBottom": "20px", "maxWidth": "500px"}),
                html.Div(id="delete-search-output"),
                html.Div(id="delete-details-container", style={"display": "none"}),
                html.Div(id="delete-confirmation-output", style={"marginTop": "20px"})
            ], style={"padding": "20px"})
        ])
    ], id="tabs", active_tab="add-new"),
    
    # Modal for duplicate warning
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle("Individual Already Exists")),
        dbc.ModalBody(id="modal-body-text"),
        dbc.ModalFooter(
            dbc.Button("Close", id="close-modal", className="ms-auto", n_clicks=0)
        ),
    ], id="modal-duplicate", is_open=False),
    
], style={"padding": "20px"})

def read_csv_safely(path):
    """Read CSV with different encodings"""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            # Strip column names
            df.columns = df.columns.str.strip()
            return df
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to read CSV with any known encoding.")

@app.callback(
    Output('expected-columns-display', 'children'),
    Input('upload-projects-data', 'id')
)
def display_expected_columns(_):
    """Display the expected column headers"""
    try:
        df_existing = read_csv_safely(CSV_PATH)
        cols = df_existing.columns.tolist()
        return html.Div(", ".join(cols))
    except:
        return "Unable to load current column structure"

def get_current_data_preview():
    """Always read current data directly from CSV file and show ALL records"""
    try:
        current_df = read_csv_safely(CSV_PATH)
        preview_table = dbc.Table.from_dataframe(
            current_df,  # Show all data, not just head(10)
            striped=True, 
            bordered=True, 
            hover=True,
            size='sm',
            style={'fontSize': '12px'}
        )
        return html.Div([
            html.P(f"Total Records: {len(current_df)}", style={"fontWeight": "bold", "marginBottom": "10px"}),
            html.Div(preview_table, style={"overflowX": "auto", "maxHeight": "600px", "overflowY": "auto"})
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading current data: {str(e)}", color="warning")

@app.callback(
    Output('upload-projects-output', 'children'),
    Output('current-projects-preview', 'children'),
    Input('upload-projects-data', 'contents'),
    State('upload-projects-data', 'filename'),
    prevent_initial_call=False
)
def update_projects_data(contents, filename):
    # If no file uploaded, just show current preview from CSV
    if contents is None:
        return html.Div(), get_current_data_preview()
    
    # Process uploaded file
    try:
        # Decode the uploaded file
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        # Check if file is Excel
        if not filename.endswith('.xlsx') and not filename.endswith('.xls'):
            return dbc.Alert("Error: Please upload an Excel file (.xlsx or .xls)", color="danger"), get_current_data_preview()
        
        # Read Excel file
        df_new = pd.read_excel(io.BytesIO(decoded), dtype=str)
        # Strip column names
        df_new.columns = df_new.columns.str.strip()
        
        # Read existing CSV
        df_existing = read_csv_safely(CSV_PATH)
        existing_columns = df_existing.columns.tolist()
        
        # Check if uploaded file has the same columns
        uploaded_columns = df_new.columns.tolist()
        
        # Find matching and missing columns
        matching_columns = [col for col in uploaded_columns if col in existing_columns]
        missing_in_upload = [col for col in existing_columns if col not in uploaded_columns]
        extra_in_upload = [col for col in uploaded_columns if col not in existing_columns]
        
        # If there are no matching columns, reject the upload
        if not matching_columns:
            error_msg = html.Div([
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
                    "Error: No matching column headers found!"
                ], color="danger"),
                html.H6("Expected columns:", style={"marginTop": "15px"}),
                html.P(", ".join(existing_columns), style={"fontSize": "12px", "color": "#666"}),
                html.H6("Found columns:", style={"marginTop": "15px"}),
                html.P(", ".join(uploaded_columns), style={"fontSize": "12px", "color": "#666"})
            ])
            return error_msg, get_current_data_preview()
        
        # Only keep matching columns from uploaded data
        df_new_filtered = df_new[matching_columns].copy()
        
        # Add missing columns with empty values
        for col in missing_in_upload:
            df_new_filtered[col] = ""
        
        # Reorder columns to match existing structure
        df_new_filtered = df_new_filtered[existing_columns]
        
        # Update existing rows or add new rows based on E.No. + Project Title combination
        rows_to_add = []
        rows_updated = []
        
        # Create a copy of existing data for modification
        df_combined = df_existing.copy()
        
        for idx, new_row in df_new_filtered.iterrows():
            # Normalize the values for comparison (handle NaN, None, empty strings)
            new_eno = str(new_row.get("E.No.", "")).strip().lower()
            new_project = str(new_row.get("Project Title", "")).strip().lower()
            
            # Replace nan/none strings with empty
            if new_eno in ["nan", "none"]:
                new_eno = ""
            if new_project in ["nan", "none"]:
                new_project = ""
            
            # Only try to match if at least ONE field (E.No. OR Project Title) is not empty
            # This prevents multiple empty rows from all matching the same existing empty row
            existing_match = False
            match_idx = None
            
            if (new_eno != "" or new_project != "") and "E.No." in df_existing.columns and "Project Title" in df_existing.columns:
                # Find matching rows by E.No. AND Project Title
                for existing_idx in df_combined.index:
                    existing_eno = str(df_combined.at[existing_idx, "E.No."]).strip().lower()
                    existing_project = str(df_combined.at[existing_idx, "Project Title"]).strip().lower()
                    
                    # Replace nan/none strings with empty
                    if existing_eno in ["nan", "none"]:
                        existing_eno = ""
                    if existing_project in ["nan", "none"]:
                        existing_project = ""
                    
                    # If both E.No. and Project Title match, it's an existing record to update
                    if new_eno == existing_eno and new_project == existing_project:
                        existing_match = True
                        match_idx = existing_idx
                        break
            
            if existing_match and match_idx is not None:
                # Update existing row with new values
                for col in existing_columns:
                    new_value = str(new_row.get(col, "")).strip()
                    # Update with new value regardless (even if empty, to allow clearing fields)
                    df_combined.at[match_idx, col] = new_value if new_value not in ["nan", "None"] else ""
                
                rows_updated.append({
                    "E.No.": new_eno,
                    "Project Title": new_project,
                    "Name": str(new_row.get("Name", "")).strip()
                })
            else:
                # Add as new row if E.No. + Project Title combination doesn't exist
                rows_to_add.append(new_row)
        
        # Add new rows that don't have matching E.No. + Project Title combination
        if rows_to_add:
            df_new_rows = pd.DataFrame(rows_to_add)
            df_combined = pd.concat([df_combined, df_new_rows], ignore_index=True)
        
        # Count records that were added and updated
        records_added = len(rows_to_add)
        records_updated = len(rows_updated)
        
        # Save combined data to CSV with proper flushing
        save_csv_safely(df_combined, CSV_PATH)
        
        # Read the updated CSV file directly from disk
        df_updated = read_csv_safely(CSV_PATH)
        
        # Create success message
        success_parts = [
            dbc.Alert([
                html.I(className="fas fa-check-circle", style={"marginRight": "10px"}),
                f"Success! {records_added} new records added, {records_updated} records updated. Total records: {len(df_updated)}"
            ], color="success")
        ]

        
        # Show info about records updated
        if records_updated > 0:
            success_parts.append(
                dbc.Alert([
                    html.I(className="fas fa-sync-alt", style={"marginRight": "10px"}),
                    f"Updated {records_updated} existing records based on Employee No. + Project Title match"
                ], color="info", style={"fontSize": "12px"})
            )
        
        # Show warnings if there were missing/extra columns
        if missing_in_upload:
            success_parts.append(
                dbc.Alert([
                    html.I(className="fas fa-info-circle", style={"marginRight": "10px"}),
                    f"Missing columns (filled with empty values): {', '.join(missing_in_upload)}"
                ], color="info", style={"fontSize": "12px"})
            )
        
        if extra_in_upload:
            success_parts.append(
                dbc.Alert([
                    html.I(className="fas fa-exclamation-circle", style={"marginRight": "10px"}),
                    f"Extra columns (ignored): {', '.join(extra_in_upload)}"
                ], color="warning", style={"fontSize": "12px"})
            )
        
        # Show ALL uploaded data from the actual CSV file (all new records that were just added)
        # Get the last 'records_added' number of rows to show exactly what was uploaded
        if records_added > 0:
            df_newly_added = df_updated.tail(records_added)
            
            success_parts.extend([
                html.H5(f"Newly Added Records Preview ({records_added} Records):", style={"marginTop": "20px", "marginBottom": "10px"}),
                html.Div(
                    dbc.Table.from_dataframe(
                        df_newly_added,  # Show all newly added records
                        striped=True, 
                        bordered=True, 
                        hover=True,
                        size='sm',
                        style={'fontSize': '12px'}
                    ),
                    style={"overflowX": "auto", "maxHeight": "600px", "overflowY": "auto"}
                )
            ])
        elif records_updated > 0:
            success_parts.append(
                dbc.Alert([
                    html.I(className="fas fa-info-circle", style={"marginRight": "10px"}),
                    f"No new records were added. {records_updated} existing records were updated."
                ], color="info")
            )
        
        success_msg = html.Div(success_parts)
        
        # Update current preview by reading directly from CSV file - show ALL data
        new_preview = html.Div([
            html.P(f"Total Records: {len(df_updated)} (Added: {records_added}, Updated: {records_updated})", 
                   style={"fontWeight": "bold", "marginBottom": "10px", "color": "green"}),
            html.Div(
                dbc.Table.from_dataframe(
                    df_updated,  # Show all records from CSV
                    striped=True, 
                    bordered=True, 
                    hover=True,
                    size='sm',
                    style={'fontSize': '12px'}
                ),
                style={"overflowX": "auto", "maxHeight": "600px", "overflowY": "auto"}
            ),
            html.P("Showing all records from CSV", style={"fontSize": "12px", "color": "#666", "marginTop": "10px"})
        ])
        
        return success_msg, new_preview
        
    except Exception as e:
        error_msg = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
            f"Error processing file: {str(e)}"
        ], color="danger")
        return error_msg, get_current_data_preview()

# ============================================
# NEW CALLBACKS FOR ADD NEW & EDIT FEATURES
# ============================================

@app.callback(
    Output('add-new-form-container', 'children'),
    Input('tabs', 'active_tab')
)
def generate_add_new_form(active_tab):
    """Generate form for adding new individual"""
    if active_tab != "add-new":
        return html.Div()
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        columns = df_existing.columns.tolist()
        
        # Define dropdown options for specific fields
        dropdown_options = {
            "Zone": ["AGGLOMERATION", "COKE OVEN", "IRON", "MILLS", "MINES", "OXYGEN", "PROJECTS", "RMHS", "SERVICE", "STEEL"],
            "Department": ["Blast Furnace-1,2", "Blast Furnace-3,4", "Blast Furnace-5", "BRM-1", "BRM-2", "CMD", 
                          "Coke Oven-3,4", "Coke Oven-5", "Corex-1,2", "CPD", "CRM-1", "CRM-2", "Digitalization", "DRI",
                          "Energy Management", "Environment Management", "HSM 2", "HSM-1", "HSM-2", "HSM-3", "Human Resources",
                          "IT", "LCP-1,2,3", "Logistics", "Marketing & CSD", "Mines", "MSDS", "OBP-2", "Oxygen", "PDQC",
                          "Pellet Plant-1", "Pellet Plant-2", "Pellet Plant-3", "PPC", "Projects", "R&D", "Refractories",
                          "RMHS", "RMHS-5MT", "RMHS-7MT", "RMHS-Basemix", "RMHS-BP2/EY", "Safety", "SEED", "Sinter Plant-1",
                          "SInter Plant-2,3,4", "Sinter Plant-5", "SMS-1", "SMS-2", "SMS-3", "SMS-4", "Technology Excellence",
                          "Utilities", "WRM-1", "WRM-2"],
            "Status": ["(Blanks)", "Analyse", "Completed", "Completed but vetting not done","Financial vetting pending","Define", "dropped", 
                      "Improve", "Measure", "Not Initiated", "Project completed but PPT is due", "Review is pending", "Review pending"],
            "Vetting status(YES/NO)": ["Yes", "No"],
            "Certification": ["YES", "NO"],
            "LSSGB/LSSBB": ["BB", "GB"],
            "Grade": ["L05", "L06", "L07", "L08", "L08T", "L09", "L10", "L11", "L12", "L13", "L14", "L16"],
            "Resigned": ["(Blanks)", "Not attended", "Resigned", "Retired", "Transferred"]
        }
        
        form_fields = []
        for col in columns:
            if col not in ["S.No", "Column2", "master list", "diff"]:  # Skip auto-generated columns
                # Check if this column should have a dropdown
                if col in dropdown_options:
                    options = [{"label": opt, "value": opt} for opt in dropdown_options[col]]
                    form_fields.append(
                        dbc.Row([
                            dbc.Col(
                                dbc.Label(col, style={"fontWeight": "600"}),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id={"type": "add-input", "index": col},
                                    options=options,
                                    placeholder=f"Select {col}",
                                    clearable=True
                                ),
                                width=9
                            )
                        ], style={"marginBottom": "15px"})
                    )
                else:
                    # Regular text input for other fields
                    form_fields.append(
                        dbc.Row([
                            dbc.Col(
                                dbc.Label(col, style={"fontWeight": "600"}),
                                width=3
                            ),
                            dbc.Col(
                                dbc.Input(id={"type": "add-input", "index": col}, placeholder=f"Enter {col}", type="text"),
                                width=9
                            )
                        ], style={"marginBottom": "15px"})
                    )
        
        return html.Div(form_fields)
    except Exception as e:
        return dbc.Alert(f"Error loading form: {str(e)}", color="danger")

@app.callback(
    Output('add-new-output', 'children'),
    Output('modal-duplicate', 'is_open'),
    Output('modal-body-text', 'children'),
    Input('btn-add-new', 'n_clicks'),
    State({'type': 'add-input', 'index': dash.dependencies.ALL}, 'value'),
    State({'type': 'add-input', 'index': dash.dependencies.ALL}, 'id'),
    prevent_initial_call=True
)
def add_new_individual(n_clicks, values, ids):
    """Add new individual to database"""
    if not n_clicks:
        return html.Div(), False, ""
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        columns = df_existing.columns.tolist()
        
        # Create new row dictionary
        new_row = {}
        for i, field_id in enumerate(ids):
            col_name = field_id['index']
            value = values[i] if values[i] else ""
            new_row[col_name] = value
        
        # Get E.No. and Project Title for duplicate check
        new_eno = str(new_row.get("E.No.", "")).strip().lower()
        new_project = str(new_row.get("Project Title", "")).strip().lower()
        
        if new_eno in ["nan", "none"]:
            new_eno = ""
        if new_project in ["nan", "none"]:
            new_project = ""
        
        # Check for duplicates
        if new_eno or new_project:
            for _, existing_row in df_existing.iterrows():
                existing_eno = str(existing_row.get("E.No.", "")).strip().lower()
                existing_project = str(existing_row.get("Project Title", "")).strip().lower()
                
                if existing_eno in ["nan", "none"]:
                    existing_eno = ""
                if existing_project in ["nan", "none"]:
                    existing_project = ""
                
                # If both match, it's a duplicate
                if new_eno == existing_eno and new_project == existing_project and new_eno != "" and new_project != "":
                    modal_text = f"Individual with Employee No: {new_row.get('E.No.', 'N/A')} and Project Title: {new_row.get('Project Title', 'N/A')} already exists in the database."
                    return html.Div(), True, modal_text
        
        # Add missing columns with empty values
        for col in columns:
            if col not in new_row:
                new_row[col] = ""
        
        # Create dataframe with new row
        new_df = pd.DataFrame([new_row])
        new_df = new_df[columns]  # Reorder columns
        
        # Append to existing data
        df_combined = pd.concat([df_existing, new_df], ignore_index=True)
        
        # Save to CSV
        save_csv_safely(df_combined, CSV_PATH)
        
        success_msg = dbc.Alert([
            html.I(className="fas fa-check-circle", style={"marginRight": "10px"}),
            f"Success! New individual added. Total records: {len(df_combined)}"
        ], color="success")
        
        return success_msg, False, ""
        
    except Exception as e:
        error_msg = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
            f"Error adding individual: {str(e)}"
        ], color="danger")
        return error_msg, False, ""

@app.callback(
    Output('modal-duplicate', 'is_open', allow_duplicate=True),
    Input('close-modal', 'n_clicks'),
    State('modal-duplicate', 'is_open'),
    prevent_initial_call=True
)
def close_modal(n_clicks, is_open):
    """Close modal"""
    if n_clicks and is_open:
        return False
    return is_open

@app.callback(
    Output('edit-form-output', 'children'),
    Output('edit-form-container', 'children'),
    Output('edit-form-container', 'style'),
    Input('btn-search-eno', 'n_clicks'),
    State('search-eno', 'value'),
    prevent_initial_call=True
)
def search_employee(n_clicks, eno):
    """Search for employee by E.No."""
    if not n_clicks or not eno:
        return dbc.Alert("Please enter an Employee No.", color="warning"), html.Div(), {"display": "none"}
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        columns = df_existing.columns.tolist()
        
        # Search for matching E.No.
        search_eno = str(eno).strip().lower()
        matching_rows = []
        matching_indices = []
        
        for idx, row in df_existing.iterrows():
            existing_eno = str(row.get("E.No.", "")).strip().lower()
            if existing_eno == search_eno:
                matching_rows.append(row)
                matching_indices.append(idx)
        
        if not matching_rows:
            return dbc.Alert(f"No individual found with Employee No: {eno}", color="warning"), html.Div(), {"display": "none"}
        
        # If multiple matches, show all
        if len(matching_rows) > 1:
            info_msg = dbc.Alert(f"Found {len(matching_rows)} records with Employee No: {eno}. Showing first match.", color="info")
        else:
            info_msg = dbc.Alert(f"Individual found! Edit the details below.", color="success")
        
        # Use first matching row
        row_data = matching_rows[0]
        row_idx = matching_indices[0]
        
        # Define dropdown options for specific fields
        dropdown_options = {
            "Zone": ["AGGLOMERATION", "COKE OVEN", "IRON", "MILLS", "MINES", "OXYGEN", "PROJECTS", "RMHS", "SERVICE", "STEEL"],
            "Department": ["Blast Furnace-1,2", "Blast Furnace-3,4", "Blast Furnace-5", "BRM-1", "BRM-2", "CMD", 
                          "Coke Oven-3,4", "Coke Oven-5", "Corex-1,2", "CPD", "CRM-1", "CRM-2", "Digitalization", "DRI",
                          "Energy Management", "Environment Management", "HSM 2", "HSM-1", "HSM-2", "HSM-3", "Human Resources",
                          "IT", "LCP-1,2,3", "Logistics", "Marketing & CSD", "Mines", "MSDS", "OBP-2", "Oxygen", "PDQC",
                          "Pellet Plant-1", "Pellet Plant-2", "Pellet Plant-3", "PPC", "Projects", "R&D", "Refractories",
                          "RMHS", "RMHS-5MT", "RMHS-7MT", "RMHS-Basemix", "RMHS-BP2/EY", "Safety", "SEED", "Sinter Plant-1",
                          "SInter Plant-2,3,4", "Sinter Plant-5", "SMS-1", "SMS-2", "SMS-3", "SMS-4", "Technology Excellence",
                          "Utilities", "WRM-1", "WRM-2"],
            "Status": ["(Blanks)", "Analyse", "Completed", "Completed but vetting not done","Financial vetting pending", "Define", "dropped", 
                      "Improve", "Measure", "Not Initiated", "Project completed but PPT is due", "Review is pending", "Review pending"],
            "Vetting status(YES/NO)": ["Yes", "No"],
            "Certification": ["YES", "NO"],
            "LSSGB/LSSBB": ["BB", "GB"],
            "Grade": ["L05", "L06", "L07", "L08", "L08T", "L09", "L10", "L11", "L12", "L13", "L14", "L16"],
            "Resigned": ["(Blanks)", "Not attended", "Resigned", "Retired", "Transferred"]
        }
        
        # Generate edit form
        form_fields = []
        for col in columns:
            if col not in ["S.No", "Column2", "master list", "diff"]:
                current_value = str(row_data.get(col, ""))
                if current_value in ["nan", "None"]:
                    current_value = ""
                
                # Check if this column should have a dropdown
                if col in dropdown_options:
                    options = [{"label": opt, "value": opt} for opt in dropdown_options[col]]
                    form_fields.append(
                        dbc.Row([
                            dbc.Col(
                                dbc.Label(col, style={"fontWeight": "600"}),
                                width=3
                            ),
                            dbc.Col(
                                dcc.Dropdown(
                                    id={"type": "edit-input", "index": col},
                                    options=options,
                                    value=current_value if current_value else None,
                                    placeholder=f"Select {col}",
                                    clearable=True
                                ),
                                width=9
                            )
                        ], style={"marginBottom": "15px"})
                    )
                else:
                    # Regular text input for other fields
                    form_fields.append(
                        dbc.Row([
                            dbc.Col(
                                dbc.Label(col, style={"fontWeight": "600"}),
                                width=3
                            ),
                            dbc.Col(
                                dbc.Input(
                                    id={"type": "edit-input", "index": col}, 
                                    value=current_value,
                                    placeholder=f"Enter {col}", 
                                    type="text"
                                ),
                                width=9
                            )
                        ], style={"marginBottom": "15px"})
                    )
        
        form_fields.append(
            html.Div([
                dbc.Button("Save and Upload", id="btn-save-edit", color="primary", size="lg", className="me-2"),
                dcc.Store(id="edit-row-index", data=row_idx)
            ], style={"marginTop": "20px"})
        )
        
        return info_msg, html.Div(form_fields), {"display": "block"}
        
    except Exception as e:
        error_msg = dbc.Alert(f"Error searching: {str(e)}", color="danger")
        return error_msg, html.Div(), {"display": "none"}

@app.callback(
    Output('edit-save-output', 'children'),
    Input('btn-save-edit', 'n_clicks'),
    State({'type': 'edit-input', 'index': dash.dependencies.ALL}, 'value'),
    State({'type': 'edit-input', 'index': dash.dependencies.ALL}, 'id'),
    State('edit-row-index', 'data'),
    prevent_initial_call=True
)
def save_edited_individual(n_clicks, values, ids, row_idx):
    """Save edited individual data"""
    if not n_clicks:
        return html.Div()
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        
        # Update the specific row
        for i, field_id in enumerate(ids):
            col_name = field_id['index']
            value = values[i] if values[i] else ""
            if value in ["nan", "None"]:
                value = ""
            df_existing.at[row_idx, col_name] = value
        
        # Save to CSV
        save_csv_safely(df_existing, CSV_PATH)
        
        success_msg = dbc.Alert([
            html.I(className="fas fa-check-circle", style={"marginRight": "10px"}),
            f"Success! Individual data updated for Employee No: {df_existing.at[row_idx, 'E.No.']}"
        ], color="success")
        
        return success_msg
        
    except Exception as e:
        error_msg = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
            f"Error saving changes: {str(e)}"
        ], color="danger")
        return error_msg

@app.callback(
    Output('delete-search-output', 'children'),
    Output('delete-details-container', 'children'),
    Output('delete-details-container', 'style'),
    Input('btn-delete-search-eno', 'n_clicks'),
    State('delete-search-eno', 'value'),
    prevent_initial_call=True
)
def search_employee_for_delete(n_clicks, eno):
    """Search for employee by E.No. for deletion"""
    if not n_clicks or not eno:
        return dbc.Alert("Please enter an Employee No.", color="warning"), html.Div(), {"display": "none"}
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        columns = df_existing.columns.tolist()
        
        # Search for matching E.No.
        search_eno = str(eno).strip().lower()
        matching_rows = []
        matching_indices = []
        
        for idx, row in df_existing.iterrows():
            existing_eno = str(row.get("E.No.", "")).strip().lower()
            if existing_eno == search_eno:
                matching_rows.append(row)
                matching_indices.append(idx)
        
        if not matching_rows:
            return dbc.Alert(f"No individual found with Employee No: {eno}", color="warning"), html.Div(), {"display": "none"}
        
        # If multiple matches, show warning
        if len(matching_rows) > 1:
            info_msg = dbc.Alert(f"Found {len(matching_rows)} records with Employee No: {eno}. Showing all matches.", color="info")
        else:
            info_msg = dbc.Alert(f"Individual found! Review details below before deleting.", color="info")
        
        # Display all matching records
        details_display = []
        for i, (row_data, row_idx) in enumerate(zip(matching_rows, matching_indices)):
            # Create a display of all fields
            field_display = []
            for col in columns:
                if col not in ["S.No", "Column2", "master list", "diff"]:
                    current_value = str(row_data.get(col, ""))
                    if current_value in ["nan", "None"]:
                        current_value = ""
                    
                    field_display.append(
                        dbc.Row([
                            dbc.Col(
                                html.Strong(f"{col}:"),
                                width=3
                            ),
                            dbc.Col(
                                html.Span(current_value if current_value else "(Empty)"),
                                width=9
                            )
                        ], style={"marginBottom": "10px", "padding": "5px", "backgroundColor": "#f8f9fa", "borderRadius": "5px"})
                    )
            
            details_display.append(
                html.Div([
                    html.H5(f"Record {i+1} of {len(matching_rows)}", style={"marginTop": "20px", "marginBottom": "15px", "color": "#dc3545"}),
                    html.Div(field_display, style={"marginBottom": "20px"}),
                    dbc.Button(
                        "Delete This Record", 
                        id={"type": "btn-delete-record", "index": row_idx}, 
                        color="danger", 
                        size="lg",
                        style={"marginBottom": "20px"}
                    ),
                    dcc.Store(id={"type": "delete-row-index", "index": row_idx}, data=row_idx),
                    html.Hr() if i < len(matching_rows) - 1 else html.Div()
                ])
            )
        
        return info_msg, html.Div(details_display), {"display": "block"}
        
    except Exception as e:
        error_msg = dbc.Alert(f"Error searching: {str(e)}", color="danger")
        return error_msg, html.Div(), {"display": "none"}

@app.callback(
    Output('delete-confirmation-output', 'children'),
    Input({'type': 'btn-delete-record', 'index': dash.dependencies.ALL}, 'n_clicks'),
    State({'type': 'delete-row-index', 'index': dash.dependencies.ALL}, 'data'),
    prevent_initial_call=True
)
def delete_individual(n_clicks_list, row_indices):
    """Delete individual from database"""
    # Check if any delete button was clicked
    if not any(n_clicks_list):
        return html.Div()
    
    # Find which button was clicked
    clicked_index = None
    for i, n_clicks in enumerate(n_clicks_list):
        if n_clicks:
            clicked_index = row_indices[i]
            break
    
    if clicked_index is None:
        return html.Div()
    
    try:
        df_existing = read_csv_safely(CSV_PATH)
        
        # Get employee details before deletion
        deleted_eno = df_existing.at[clicked_index, 'E.No.']
        deleted_name = df_existing.at[clicked_index, 'Name']
        
        # Delete the row
        df_existing = df_existing.drop(clicked_index).reset_index(drop=True)
        
        # Save to CSV
        save_csv_safely(df_existing, CSV_PATH)
        
        success_msg = dbc.Alert([
            html.I(className="fas fa-check-circle", style={"marginRight": "10px"}),
            f"Success! Individual deleted. Employee No: {deleted_eno}, Name: {deleted_name}. Total records remaining: {len(df_existing)}"
        ], color="success")
        
        return success_msg
        
    except Exception as e:
        error_msg = dbc.Alert([
            html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
            f"Error deleting individual: {str(e)}"
        ], color="danger")
        return error_msg
