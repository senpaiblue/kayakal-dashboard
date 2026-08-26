import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from app import app
import pandas as pd
import base64
import io
import os
import tempfile
from pathlib import Path
from datetime import datetime, timedelta


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "Data"
CSV_PATH = str(DATA_DIR / "opl_pokayoke.csv")
UPLOADED_EXCEL_CONVERTED_CSV_PATH = str(DATA_DIR / "opl_pokayoke_uploaded_excel_converted.csv")
DATE_COL = "TransactionDate"
DATE_FORMAT = "%d-%m-%Y"

def save_csv_safely(df, path):
    """Save CSV with proper flushing to disk"""
    df.to_csv(path, index=False, encoding='utf-8')
    try:
        if hasattr(os, 'sync'):
            os.sync()
    except:
        pass

def read_uploaded_excel_safely(decoded, filename):
    """Read uploaded Excel without relying on openpyxl style parsing."""
    import python_calamine

    suffix = Path(filename or "upload.xlsx").suffix or ".xlsx"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=True) as tmp:
        tmp.write(decoded)
        tmp.flush()

        workbook = python_calamine.CalamineWorkbook.from_path(tmp.name)
        sheet = workbook.get_sheet_by_index(0)
        rows = sheet.to_python(skip_empty_area=False)

    if not rows:
        return pd.DataFrame()

    headers = [str(header).strip() if header is not None else "" for header in rows[0]]
    data = [
        [str(cell).strip() if cell is not None else "" for cell in row]
        for row in rows[1:]
    ]
    return pd.DataFrame(data, columns=headers)

def parse_uploaded_file(contents, filename):
    """Parse uploaded CSV/Excel and return normalized dataframe."""
    _, content_string = contents.split(",", 1)
    decoded = base64.b64decode(content_string)
    fname = (filename or "").lower()

    if fname.endswith(".csv"):
        last_error = None
        for enc in ["utf-8", "utf-8-sig", "cp1252", "latin1"]:
            try:
                return pd.read_csv(io.StringIO(decoded.decode(enc)), dtype=str)
            except Exception as err:
                last_error = err
        raise ValueError(f"Unable to decode CSV with supported encodings: {last_error}")

    if fname.endswith(".xlsx") or fname.endswith(".xls"):
        df_excel = read_uploaded_excel_safely(decoded, filename)
        # Always convert uploaded Excel into CSV so downstream reads are CSV-native.
        save_csv_safely(df_excel, UPLOADED_EXCEL_CONVERTED_CSV_PATH)
        return df_excel

    raise ValueError("Please upload a .csv, .xlsx, or .xls file")

def normalize_text_columns(df, columns):
    """Normalize selected columns for safe dedupe comparisons."""
    out = df.copy()
    for col in columns:
        if col in out.columns:
            out[col] = out[col].fillna("").astype(str).str.strip()
    return out

def choose_merge_key(uploaded_columns, existing_columns):
    """Use the stable submission reference before falling back to legacy ID."""
    for col in ["TransactionRefNo", "ID"]:
        if col in uploaded_columns and col in existing_columns:
            return col
    return None

layout = html.Div([
    html.H2("OPL/Poka Yoke Data Management", style={"marginBottom": "30px", "color": "#0d6efd"}),
    
    html.Div([
        html.Div([
            html.Small("Expected column headers :", style={"fontWeight": "600", "color": "#666", "marginTop": "20px", "display": "block"}),
            html.Div(id="opl-expected-columns-display", style={"fontSize": "11px", "color": "#999", "marginBottom": "15px"})
        ]),
        
        html.P("Upload a new Excel (.xlsx) or CSV (.csv) file to update data.", 
               style={"fontSize": "16px", "color": "#666", "marginBottom": "10px"}),
        html.P("Note: Column headers must exactly match the existing data. Rows with matching 'TransactionRefNo' will be updated.", 
               style={"fontSize": "14px", "color": "#e74c3c", "marginBottom": "5px", "fontStyle": "italic", "fontWeight": "600"}),
        
        html.Div([
            html.Small("Last updated (by TransactionDate): "),
            html.B(id="opl-last-updated-date")
        ], className="mb-3"),
        
        dcc.Upload(
            id='upload-opl-data',
            children=html.Div([
                html.I(className="fas fa-cloud-upload-alt", style={"fontSize": "48px", "color": "#0d6efd", "marginBottom": "15px"}),
                html.P('Drag and Drop or Click to Select File (.csv, .xlsx)', 
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
                'justifyContent': 'center'
            },
            multiple=False,
            accept=".csv,.xls,.xlsx"
        ),
        
        html.Div(id='upload-opl-output', style={"marginTop": "20px"}),
        
        html.Hr(style={"margin": "40px 0"}),
        
        html.H4("Current Data Preview (All Records)", style={"marginBottom": "20px", "color": "#333"}),
        html.Div(id='current-opl-preview')
        
    ], style={"padding": "20px", "maxWidth": "1200px", "backgroundColor": "white", "borderRadius": "8px", "border": "1px solid #d0d7de"})
], style={"padding": "20px"})

def read_csv_safely(path):
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            df.columns = df.columns.str.strip()
            return df
        except:
            pass
    # If file doesn't exist, return empty dataframe with expected columns
    return pd.DataFrame(columns=[
        "ID","TransactionRefNo","TICName","Department","Theme",
        "TransactionDate","Impact","Source","Classification",
        "Objective","Function","State","TangiblegainsRsperannum",
        "ChampionRemarks","ChampionApprovalDate",
        "ImplementedByFirstPerson","Emp1Code","Emp1Grade",
        "Emp1Organization","ImplementedBySecondPerson","Emp2Code",
        "EMP2Grade","EMP2Organization","FAUploadedDocument"
    ])

def get_opl_last_saved_date():
    df = read_csv_safely(CSV_PATH)
    if df.empty or DATE_COL not in df.columns:
        return None
    dates = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    dates_clean = dates.dropna()
    if dates_clean.empty:
        return None
    res = dates_clean.max()
    if pd.isna(res):
        return None
    return res

def get_opl_last_updated_str():
    try:
        last_date = get_opl_last_saved_date()
        if last_date is None or pd.isna(last_date):
            return "No transactions yet"
        return last_date.strftime(DATE_FORMAT)
    except Exception:
        return "No transactions yet"

# Helper to normalize date values to DD-MM-YYYY format
def normalize_date_value(val):
    if val is None or pd.isna(val):
        return ""
    s = str(val).strip()
    if s == "" or s.lower() in ["nan", "none", "nat"]:
        return ""
    
    # Try common formats
    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%d-%m-%Y")
        except:
            pass
            
    # Try pandas to_datetime
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if not pd.isna(dt):
            return dt.strftime("%d-%m-%Y")
    except:
        pass
        
    # Try Excel serial date
    try:
        if s.replace(",", "").replace(".", "", 1).isdigit():
            dt = datetime(1899, 12, 30) + timedelta(days=int(float(s)))
            return dt.strftime("%d-%m-%Y")
    except:
        pass
        
    return s  # Return original if parsing fails

@app.callback(
    Output('opl-expected-columns-display', 'children'),
    Input('upload-opl-data', 'id')
)
def opl_display_expected_columns(_):
    try:
        df_existing = read_csv_safely(CSV_PATH)
        cols = df_existing.columns.tolist()
        return html.Div(", ".join(cols))
    except:
        return "Unable to load current column structure"

def get_current_data_preview():
    try:
        current_df = read_csv_safely(CSV_PATH)
        preview_table = dbc.Table.from_dataframe(
            current_df.head(50),  # Show top 50
            striped=True, 
            bordered=True, 
            hover=True,
            size='sm',
            style={'fontSize': '12px'}
        )
        return html.Div([
            html.P(f"Total Records: {len(current_df)} (Showing top 50)", style={"fontWeight": "bold", "marginBottom": "10px"}),
            html.Div(preview_table, style={"overflowX": "auto", "maxHeight": "600px", "overflowY": "auto"})
        ])
    except Exception as e:
        return dbc.Alert(f"Error loading current data: {str(e)}", color="warning")

@app.callback(
    Output('upload-opl-output', 'children'),
    Output('current-opl-preview', 'children'),
    Output('opl-last-updated-date', 'children'),
    Input('upload-opl-data', 'contents'),
    State('upload-opl-data', 'filename'),
    prevent_initial_call=False
)
def opl_update_opl_data(contents, filename):
    if contents is None:
        return html.Div(), get_current_data_preview(), get_opl_last_updated_str()
    
    try:
        df_new = parse_uploaded_file(contents, filename)
            
        df_new.columns = df_new.columns.str.strip()
        df_existing = read_csv_safely(CSV_PATH)
        existing_columns = df_existing.columns.tolist()
        
        # Convert uploaded columns to match existing columns case-insensitively
        existing_cols_lower = {col.lower(): col for col in existing_columns}
        new_columns = []
        for col in df_new.columns:
            col_lower = col.lower()
            if col_lower in existing_cols_lower:
                new_columns.append(existing_cols_lower[col_lower])
            else:
                new_columns.append(col)
        df_new.columns = new_columns
        
        uploaded_columns = df_new.columns.tolist()
        matching_columns = [col for col in uploaded_columns if col in existing_columns]
        
        if not matching_columns:
            error_msg = html.Div([
                dbc.Alert([
                    html.I(className="fas fa-exclamation-triangle", style={"marginRight": "10px"}),
                    "Error: No matching column headers found!"
                ], color="danger"),
                html.H6("Expected columns:", style={"marginTop": "15px"}),
                html.P(", ".join(existing_columns), style={"fontSize": "12px", "color": "#666"}),
                html.H6("Found columns in uploaded file:", style={"marginTop": "15px"}),
                html.P(", ".join(uploaded_columns), style={"fontSize": "12px", "color": "#666"})
            ])
            return error_msg, get_current_data_preview(), get_opl_last_updated_str()
            
        df_new_filtered = df_new[matching_columns].copy()
        df_new_filtered = normalize_text_columns(df_new_filtered, matching_columns)
        df_existing = normalize_text_columns(df_existing, existing_columns)
        
        # Normalize date values to DD-MM-YYYY format
        for col in [DATE_COL, "ChampionApprovalDate"]:
            if col in df_new_filtered.columns:
                df_new_filtered[col] = df_new_filtered[col].apply(normalize_date_value)
            if col in df_existing.columns:
                df_existing[col] = df_existing[col].apply(normalize_date_value)
        
        merge_key = choose_merge_key(matching_columns, existing_columns)

        # Merge logic based on the stable submission reference.
        if merge_key:
            # Remove duplicate keys inside uploaded file itself (keep latest occurrence).
            df_new_filtered[merge_key] = df_new_filtered[merge_key].fillna("").astype(str).str.strip()
            df_new_filtered = df_new_filtered[df_new_filtered[merge_key] != ""]
            df_new_filtered = df_new_filtered.drop_duplicates(subset=[merge_key], keep="last")

            # Set index for faster update
            df_existing.set_index(merge_key, inplace=True)
            df_new_filtered.set_index(merge_key, inplace=True)
            
            # Update existing rows
            df_existing.update(df_new_filtered)
            
            # Add new rows
            new_rows = df_new_filtered[~df_new_filtered.index.isin(df_existing.index)]
            df_combined = pd.concat([df_existing, new_rows]).reset_index()
            
        else:
            # If no ID column, append only truly new rows (skip exact duplicates).
            existing_rows = df_existing[matching_columns].copy()
            existing_keys = set(existing_rows.apply(lambda row: "|~|".join(row.values.astype(str)), axis=1).tolist())
            upload_keys = df_new_filtered.apply(lambda row: "|~|".join(row.values.astype(str)), axis=1)
            df_new_unique = df_new_filtered[~upload_keys.isin(existing_keys)].copy()
            df_combined = pd.concat([df_existing, df_new_unique], ignore_index=True)
            
        # Ensure all columns exist
        missing_cols = [c for c in existing_columns if c not in df_combined.columns]
        for c in missing_cols:
            df_combined[c] = ""
            
        df_combined = df_combined[existing_columns]

        # Final safety dedupe after merge/appends.
        if merge_key and merge_key in df_combined.columns:
            has_key = df_combined[merge_key].fillna("").astype(str).str.strip() != ""
            df_with_key = df_combined[has_key].drop_duplicates(subset=[merge_key], keep="last")
            df_without_key = df_combined[~has_key].drop_duplicates()
            df_combined = pd.concat([df_with_key, df_without_key], ignore_index=True)
        else:
            df_combined = df_combined.drop_duplicates(ignore_index=True)
            
        # Ensure NaN values are replaced with empty string before saving
        df_combined = df_combined.fillna("")
        
        save_csv_safely(df_combined, CSV_PATH)
        
        if (filename or "").lower().endswith((".xlsx", ".xls")):
            message = f"Success! Excel converted to CSV and data processed. Total rows: {len(df_combined)}"
        else:
            message = f"Success! Data processed. Total rows: {len(df_combined)}"

        success_msg = dbc.Alert([
            html.I(className="fas fa-check-circle", style={"marginRight": "10px"}),
            message
        ], color="success")
        
        return success_msg, get_current_data_preview(), get_opl_last_updated_str()
        
    except Exception as e:
        return dbc.Alert(f"Error processing file: {str(e)}", color="danger"), get_current_data_preview(), get_opl_last_updated_str()
