import os
import base64
import random
import string
from datetime import datetime

import pandas as pd
import dash
from dash import html, dcc, Output, Input, State, callback
import dash_bootstrap_components as dbc
from server import app

SAVE_DIR = "./assets/highlight/"
DT_FILE = "./assets/5s/DT.xlsx"

os.makedirs(SAVE_DIR, exist_ok=True)

def load_dt():
    df = pd.read_excel(DT_FILE, dtype=str)
    return df.fillna("")

def save_dt(df):
    df.to_excel(DT_FILE, index=False)

def generate_password(length=6):
    return ''.join(random.choices(string.digits, k=length))


layout = dbc.Container([

    html.H2("📄 Upload Spotlights PDF File", className="text-center mt-3"),

    dbc.Card([
        dbc.CardBody([
            dcc.Upload(
                id='pdf-uploader',
                accept="application/pdf",
                children=html.Div(
                    [
                        html.I(className="bi bi-cloud-upload fs-2"),
                        html.Div("Drag and Drop or"),
                        html.B("Click to Upload PDF")
                    ],
                    style={
                        "pointerEvents": "none",
                        "whiteSpace": "nowrap"
                    }
                )
                ,
                style={
                    "width": "100%",
                    "height": "160px",
                    "border": "2px dashed #0d6efd",
                    "borderRadius": "12px",
                    "textAlign": "center",
                    "backgroundColor": "#f8f9fa",
                    "cursor": "pointer",
                    "display": "flex",
                    "flexDirection": "column",
                    "alignItems": "center",
                    "justifyContent": "center",
                    "overflow": "hidden"
                },

                multiple=False
            ),
            html.Div(id="upload-status", className="mt-3 text-center")
        ])
    ], className="shadow-sm"),

  
    html.Hr(style={"borderTop": "3px solid #adb5bd", "margin": "40px 0"}),

    html.H2("📘 Upload TQM Magazine", className="text-center"),

    dbc.Card([
        dbc.CardBody([

            dbc.Row([
                dbc.Col([
                    dbc.Label("Magazine Title"),
                    dbc.Input(
                        id="mag-title",
                        placeholder="Enter Magazine Title"
                    )
                ], md=5),

                dbc.Col([
                    dbc.Label("Select PDF"),
                    dcc.Upload(
                        id="mag-pdf-upload",
                        accept=".pdf",
                        multiple=False,
                        children=html.Div([
                            "📄 Drag & Drop or ",
                            html.B("Select PDF")
                        ]),
                        className="upload-box"
                    ),
                    html.Div(
                        id="file-selected-text",
                        className="text-success mt-2 fw-semibold"
                    )
                ], md=5),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col(
                    dbc.Button(
                        "🚀 Upload Magazine",
                        id="upload-mag-btn",
                        color="primary",
                        size="lg",
                        className="upload-btn"
                    ),
                    className="text-center"
                )
            ])

        ])
    ], className="shadow-sm"),

    
    dbc.Modal([
        dbc.ModalHeader(dbc.ModalTitle(id="upload-modal-title")),
        dbc.ModalBody(id="upload-modal-body"),
        dbc.ModalFooter(
            dbc.Button("OK", id="close-upload-modal", color="primary")
        )
    ], id="upload-modal", is_open=False),

    html.Hr(style={"borderTop": "3px solid #6c757d", "margin": "40px 0"}),

    html.H3("🔐 Department / Model Password Management", className="text-center"),

    dbc.Card([
        dbc.CardBody([

            dbc.Row([
                dbc.Col([
                    dbc.Label("Department"),
                    dcc.Dropdown(id="pm-dept", placeholder="Select Department")
                ], md=4),

                dbc.Col([
                    dbc.Label("Model"),
                    dcc.Dropdown(id="pm-model", placeholder="Select Model")
                ], md=4),

                dbc.Col([
                    dbc.Label("Password"),
                    dbc.Input(
                        id="pm-password",
                        type="text",
                        placeholder="Enter or Generate Password"
                    )
                ], md=4),
            ], className="mb-3"),

            dbc.Row([
                dbc.Col(
                    dbc.Button("🔄 Generate Password", id="pm-generate", color="warning"),
                    md=3
                ),
                dbc.Col(
                    dbc.Button("💾 Update Password", id="pm-update", color="success"),
                    md=3
                )
            ], className="mb-3"),

            html.Div(id="pm-status")

        ])
    ], className="shadow-sm border border-primary")

], fluid=True)




@callback(
    Output("upload-status", "children"),
    Input("pdf-uploader", "contents"),
    State("pdf-uploader", "filename"),
    prevent_initial_call=True
)
def save_pdf(contents, filename):

    if contents is None:
        raise dash.exceptions.PreventUpdate

    
    if not filename.lower().endswith(".pdf"):
        return dbc.Alert(
            "❌ Only PDF files are allowed.",
            color="danger",
            dismissable=True
        )

    try:
        content_type, content_string = contents.split(',')

      
        if content_type != "data:application/pdf;base64":
            return dbc.Alert(
                "❌ Invalid file format. Please upload a valid PDF.",
                color="danger",
                dismissable=True
            )

        today = datetime.now().strftime("%d-%m-%Y")
        save_path = os.path.join(SAVE_DIR, f"{today}.pdf")

        decoded = base64.b64decode(content_string)

        with open(save_path, "wb") as f:
            f.write(decoded)

        return dbc.Alert(
            f"✅ PDF uploaded successfully as {today}.pdf",
            color="success",
            dismissable=True
        )

    except Exception as e:
        return dbc.Alert(
            f"❌ Error saving file: {str(e)}",
            color="danger",
            dismissable=True
        )



@callback(
    Output("pm-dept", "options"),
    Input("pm-dept", "id")
)
def load_departments(_):
    df = load_dt()
    depts = sorted(df["department"].unique())
    return [{"label": d, "value": d} for d in depts if d]


@callback(
    Output("pm-model", "options"),
    Input("pm-dept", "value")
)
def filter_models(dept):
    if not dept:
        return []
    df = load_dt()
    models = df[df["department"] == dept]["model"].unique()
    return [{"label": m, "value": m} for m in models if m]


@callback(
    Output("pm-password", "value"),
    Input("pm-generate", "n_clicks"),
    prevent_initial_call=True
)
def auto_generate(_):
    return generate_password()


@callback(
    Output("pm-status", "children"),
    Input("pm-update", "n_clicks"),
    State("pm-dept", "value"),
    State("pm-model", "value"),
    State("pm-password", "value"),
    prevent_initial_call=True
)
def update_password(_, dept, model, pwd):
    if not dept or not pwd:
        return dbc.Alert("⚠ Please select Department and enter password", color="warning")

    df = load_dt()

    mask = (df["department"] == dept) & (df["model"] == (model or ""))
    if not mask.any():
        return dbc.Alert("❌ Record not found", color="danger")

    df.loc[mask, "password"] = pwd
    save_dt(df)

    return dbc.Alert(
        "✅ Password updated successfully",
        color="success",
        dismissable=True
    )

import os
import base64
from pathlib import Path
import dash
import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output, State
from server import app
UPLOAD_FOLDER = Path("./Data/magazine")
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)


@app.callback(
    Output("file-selected-text", "children"),
    Input("mag-pdf-upload", "contents"),
    State("mag-pdf-upload", "filename"),
    prevent_initial_call=True
)
def show_selected_file(contents, filename):
    if contents and filename:
        return f"📄 File selected: {filename}"
    return ""
@app.callback(
    Output("upload-modal", "is_open"),
    Output("upload-modal-title", "children"),
    Output("upload-modal-body", "children"),
    Input("upload-mag-btn", "n_clicks"),
    Input("close-upload-modal", "n_clicks"),
    State("mag-title", "value"),
    State("mag-pdf-upload", "contents"),
    prevent_initial_call=True
)
def upload_magazine(n_upload, n_close, title, contents):

    ctx = dash.callback_context
    trigger = ctx.triggered[0]["prop_id"].split(".")[0]

   
    if trigger == "close-upload-modal":
        return False, "", ""

 
    if not title:
        return True, "❌ Upload Error", "Please enter Magazine Title."

    if not contents:
        return True, "❌ Upload Error", "Please select a PDF file."

    try:
        safe_title = title.strip().replace("/", "-").replace("\\", "-")
        file_path = UPLOAD_FOLDER / f"{safe_title}.pdf"

        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)

        with open(file_path, "wb") as f:
            f.write(decoded)

        return (
            True,
            "✅ Upload Successful",
            f"Magazine '{safe_title}' uploaded successfully."
        )

    except Exception as e:
        return (
            True,
            "❌ Upload Failed",
            f"Error occurred while uploading:\n{str(e)}"
        )      