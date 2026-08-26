

import os
import io
import base64
from datetime import datetime, timedelta
import pandas as pd

from dash import html, dcc, Input, Output, State, ctx, no_update
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

from app import app   


CSV_FILE = "Data/KZ_REPORT.csv"
DATE_COL = "TransactionDate"
DATE_FORMAT = "%d-%m-%Y"

EXPECTED_COLUMNS = [
    "KaizenID","TransactionRefNo","TICName","Department","KaizenTheme",
    "TransactionDate","KaizenImpact","SourceofKaizen","TangiblegainsRsperannum",
    "KaizenCategory","BERemarks","BEApprovalDate","ImplementedByFirstPerson",
    "Emp1Code","Emp1Grade","Emp1Organization","ImplementedBySecondPerson",
    "Emp2Code","EMP2GRADE","EMP2Organization","FAUploadedDocument"
]

VALID_STATUSES = [
    "Pending with BE",
    "Pending with Kaizen Expert",
    "Rejected by Kaizen Expert",
    "Pending with Champion",
    "Saved as Draft",
    "Returned"
]


os.makedirs(os.path.dirname(CSV_FILE) or ".", exist_ok=True)
if not os.path.exists(CSV_FILE):
    pd.DataFrame(columns=EXPECTED_COLUMNS).to_csv(CSV_FILE, index=False)


def excel_serial_to_datetime(serial):
    try:
        return datetime(1899, 12, 30) + timedelta(days=int(float(serial)))
    except Exception:
        return None

def parse_date_value(val):
    if val is None:
        return None, ""
    s = str(val).strip()

    if s == "" or s.lower() in ["nan", "none"]:
        return None, s

    for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt), s
        except Exception:
            pass

    try:
        dt = pd.to_datetime(s, dayfirst=True, errors="coerce")
        if not pd.isna(dt):
            return dt.to_pydatetime(), s
    except Exception:
        pass

    try:
        if s.replace(",", "").replace(".", "", 1).isdigit():
            return excel_serial_to_datetime(float(s)), s
    except Exception:
        pass

    return None, s

def read_master_df():
    if os.path.getsize(CSV_FILE) == 0:
        return pd.DataFrame(columns=EXPECTED_COLUMNS)
    df = pd.read_csv(CSV_FILE, dtype=str)
    df[DATE_COL] = pd.to_datetime(df[DATE_COL], dayfirst=True, errors="coerce")
    return df

def write_master_df(df):
    df_out = df.copy()
    df_out[DATE_COL] = df_out[DATE_COL].dt.strftime(DATE_FORMAT)
    df_out.to_csv(CSV_FILE, index=False)

def get_last_saved_date():
    df = read_master_df()
    if df.empty:
        return None
    return df[DATE_COL].dropna().max()

def fix_shifted_rows(df):
    corrections = []
    for i in df.index:
        first_val = str(df.iloc[i, 0]).strip()
        if first_val not in VALID_STATUSES:
            corrections.append({
                "Row": i + 1,
                "OriginalFirstValue": first_val,
                "CorrectedStatus": "Approved By All"
            })
            df.iloc[i, 0] = "Approved By All"
    return df, corrections


layout = dbc.Container([
    dcc.Store(id="uploaded-excel-store"),

    dbc.Card([
        dbc.CardHeader("Upload Excel File"),
        dbc.CardBody([

            html.Div([
                html.Small("Last updated (by TransactionDate): "),
                html.B(id="last-updated-date")
            ], className="mb-3"),

            dcc.Upload(
                id="upload-data",
                children=html.Div("Drag & Drop or Click to Upload Excel"),
                style={
                    "width": "100%",
                    "height": "90px",
                    "lineHeight": "90px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "6px",
                    "textAlign": "center"
                },
                accept=".xls,.xlsx"
            ),

            dbc.Button("Save Uploaded Data", id="save-btn", color="success", className="mt-3"),
            html.Div(id="upload-output", className="mt-3")
        ])
    ]),

    dbc.Modal(
        [
            dbc.ModalHeader("Rows Skipped"),
            dbc.ModalBody(id="modal-body"),
            dbc.ModalFooter(
                dbc.Button("Close", id="modal-close")
            )
        ],
        id="skip-modal",
        size="lg",
        is_open=False
    )
], fluid=True)


@app.callback(
    Output("uploaded-excel-store", "data"),
    Output("upload-output", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def read_excel(contents, filename):
    if not contents:
        raise PreventUpdate

    _, b64 = contents.split(",")
    df = pd.read_excel(io.BytesIO(base64.b64decode(b64)), dtype=str)
    df, corrections = fix_shifted_rows(df)

    return {
        "data": df.to_dict("records"),
        "corrections": corrections
    }, dbc.Alert(f"{filename} loaded successfully.", color="success")


@app.callback(
    Output("upload-output", "children", allow_duplicate=True),
    Output("skip-modal", "is_open"),
    Output("modal-body", "children"),
    Input("save-btn", "n_clicks"),
    Input("modal-close", "n_clicks"),
    State("uploaded-excel-store", "data"),
    prevent_initial_call=True
)
def save_uploaded_data(save_n, close_n, store):
    if ctx.triggered_id == "modal-close":
        return no_update, False, ""

    if not store:
        return dbc.Alert("No file uploaded.", color="warning"), False, ""

    df_new = pd.DataFrame(store["data"])
    df_master = read_master_df()

    rows_to_save = []
    skipped = []

    for i, row in df_new.iterrows():
        dt, orig = parse_date_value(row.get(DATE_COL))
        if not dt:
            skipped.append({"Row": i + 1, "TransactionDate": orig or "Empty/Invalid", "Reason": "Invalid Date"})
            continue
        row[DATE_COL] = dt
        rows_to_save.append(row)

    if not rows_to_save:
        table = dbc.Table.from_dataframe(pd.DataFrame(skipped), bordered=True)
        return dbc.Alert("No rows saved. All rows had invalid dates.", color="danger"), True, table

    # Simply append all valid rows (allowing duplicates as new rows)
    df_to_save = pd.DataFrame(rows_to_save)
    df_final = pd.concat([df_master, df_to_save], ignore_index=True)

    # Ensure all expected columns exist and are ordered correctly
    for col in EXPECTED_COLUMNS:
        if col not in df_final.columns:
            df_final[col] = ""
    df_final = df_final[EXPECTED_COLUMNS]

    # Sort by date and save
    df_final.sort_values(DATE_COL, inplace=True)
    write_master_df(df_final)

    success_msg = f"Saved successfully: {len(df_to_save)} rows added."
    if skipped:
        success_msg += f" ({len(skipped)} rows skipped due to invalid date)."

    return dbc.Alert(success_msg, color="success"), False, ""
@app.callback(
    Output("last-updated-date", "children"),
    Input("uploaded-excel-store", "data"),
    )
def update_last_updated_date(_):
    last_date = get_last_saved_date()

    if last_date is None:
        return "No transactions yet"

    return last_date.strftime(DATE_FORMAT)
