import dash
from dash import html, dcc, Input, Output, State, dash_table
import dash_bootstrap_components as dbc
from app import app
import pandas as pd
import base64
import io
import os
from pathlib import Path
from dash.exceptions import PreventUpdate

CSV_PATH = os.path.abspath("./Data/j1_data.csv")

def save_csv_safely(df, path):
    """Save CSV with proper flushing to disk - critical for server deployments"""
    df.to_csv(path, index=False, encoding='utf-8')
    
    try:
        if hasattr(os, 'sync'):
            os.sync()
    except:
        pass
    
    try:
        file_size = os.path.getsize(path)
        if file_size == 0:
            raise IOError(f"CSV file {path} was written but has zero size")
    except Exception as e:
        print(f"Warning: Could not verify CSV write: {e}")

layout = html.Div(
    [
        html.H2(
            "J1 Data Management",
            style={"marginBottom": "30px", "color": "#0d6efd"},
        ),
        html.Div(
            [
                html.H5(
                    "Edit Data (Copy / Paste & Save)",
                    style={"marginBottom": "10px", "color": "#333"},
                ),
                html.P(
                    "You can copy and paste data directly into the editable table below. "
                    "After making changes, click 'Save Changes' to update the CSV file.",
                    style={
                        "fontSize": "12px",
                        "color": "#666",
                        "marginBottom": "10px",
                    },
                ),
                html.Div(id="j1-edit-container"),
                html.Br(),
                html.Div(id="j1-save-status"),
                dcc.Store(id="j1-edit-refresh", data=0),
            ],
            style={"padding": "20px", "maxWidth": "1200px"},
        ),
    ],
    style={"padding": "20px"},
)

def read_csv_safely(path):
    """Read CSV with different encodings"""
    encodings = ["utf-8", "utf-8-sig", "cp1252", "latin1", "ISO-8859-1"]
    for enc in encodings:
        try:
            df = pd.read_csv(path, dtype=str, encoding=enc)
            df.columns = df.columns.str.strip()
            return df
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError("Unable to read CSV with any known encoding.")

def get_current_j1_preview():
    """
    Kept for compatibility but no longer used in the layout.
    Always reads current data directly from CSV file and shows ALL records.
    """
    try:
        if not os.path.exists(CSV_PATH):
            return dbc.Alert(
                "No data file found. Please upload data first.",
                color="info",
            )

        current_df = read_csv_safely(CSV_PATH)
        preview_table = dbc.Table.from_dataframe(
            current_df,
            striped=True,
            bordered=True,
            hover=True,
            size="sm",
            style={"fontSize": "12px"},
        )
        return html.Div(
            [
                html.P(
                    f"Total Records: {len(current_df)}",
                    style={
                        "fontWeight": "bold",
                        "marginBottom": "10px",
                    },
                ),
                html.Div(
                    preview_table,
                    style={
                        "overflowX": "auto",
                        "maxHeight": "600px",
                        "overflowY": "auto",
                    },
                ),
            ]
        )
    except Exception as e:
        return dbc.Alert(
            f"Error loading current data: {str(e)}",
            color="warning",
        )


@app.callback(
    Output("j1-edit-container", "children"),
    Input("j1-edit-refresh", "data"),
    prevent_initial_call=False,
)
def load_j1_editable_table(refresh_value):
    """
    Load the editable table used for copy / paste editing.
    This reads directly from the current CSV file.
    """
    try:
        if not os.path.exists(CSV_PATH):
            return dbc.Alert(
                "No data file found. Please upload data first.",
                color="info",
            )

        df = read_csv_safely(CSV_PATH)
        # Make every column explicitly editable on the client side
        columns = [{"name": col, "id": col, "editable": True} for col in df.columns]

        edit_table = dash_table.DataTable(
            id="j1-edit-table",
            columns=columns,
            data=df.to_dict("records"),
            editable=True,
            persistence=True,
            persisted_props=["data"],
            persistence_type="memory",
            row_deletable=True,
            page_size=20,
            style_table={
                "overflowX": "auto",
                "maxHeight": "600px",
                "overflowY": "auto",
            },
            style_cell={
                "fontSize": 12,
                "textAlign": "left",
                "minWidth": "120px",
                "width": "120px",
                "maxWidth": "250px",
                "whiteSpace": "normal",
            },
        )

        return html.Div(
            [
                edit_table,
                html.Br(),
                dbc.Button(
                    "Save Changes",
                    id="j1-save-button",
                    color="primary",
                    className="mt-2",
                ),
            ]
        )
    except Exception as e:
        return dbc.Alert(
            f"Error loading editable table: {str(e)}",
            color="warning",
        )


@app.callback(
    Output("j1-save-status", "children"),
    Output("j1-edit-refresh", "data"),
    Input("j1-save-button", "n_clicks"),
    State("j1-edit-table", "data"),
    State("j1-edit-refresh", "data"),
    prevent_initial_call=True,
)
def save_j1_edits(n_clicks, table_data, current_refresh):
    """
    Save edits made in the editable table back to the CSV.
    This enables copy / paste editing + explicit save.
    """
    if not n_clicks:
        raise PreventUpdate

    if not table_data:
        return dbc.Alert(
            "No data to save. Please paste or edit data before saving.",
            color="warning",
        ), current_refresh

    try:
        # Build DataFrame from edited table, ensuring no NaN values
        # and then persist EXACTLY what is visible in the editable table.
        # This guarantees that any cell edits for any column are written
        # directly to the CSV without being overridden by previous data.
        df = pd.DataFrame(table_data).fillna("")

        save_csv_safely(df, CSV_PATH)

        # Increment refresh value to trigger preview + editor reload
        new_refresh = (current_refresh or 0) + 1

        return dbc.Alert(
            "Changes saved successfully. Current data preview has been updated.",
            color="success",
        ), new_refresh
    except Exception as e:
        return dbc.Alert(
            f"Error saving data: {str(e)}",
            color="danger",
        ), current_refresh
