import os
import base64
import pandas as pd
from datetime import datetime

from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

from server import app

# ---------------- PATHS ---------------- #
EVENT_FOLDER = "./assets/events"
CSV_FILE = os.path.join(EVENT_FOLDER, "data.csv")

os.makedirs(EVENT_FOLDER, exist_ok=True)

# Create CSV if not exists
if not os.path.exists(CSV_FILE):
    df = pd.DataFrame(columns=["Date", "Heading", "eventdate", "image"])
    df.to_csv(CSV_FILE, index=False)

# ---------------- HELPERS ---------------- #
def get_next_image_name(extension):
    df = pd.read_csv(CSV_FILE)
    return f"event{len(df) + 1}.{extension}"

def save_image(contents, filename):
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)
    with open(filename, "wb") as f:
        f.write(decoded)

import os
import base64
import pandas as pd
from datetime import datetime

from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc

from server import app

# ---------------- PATHS ---------------- #

TRAINING_FOLDER = "./assets/training"
NEWSLETTER_FOLDER = "./assets/newsletter"

CSV_FILE = os.path.join(EVENT_FOLDER, "data.csv")

for folder in [EVENT_FOLDER, TRAINING_FOLDER, NEWSLETTER_FOLDER]:
    os.makedirs(folder, exist_ok=True)



# ---------------- HELPERS ---------------- #


def month_options():
    return [
        {"label": datetime(2000, i, 1).strftime("%B"), "value": i}
        for i in range(1, 13)
    ]

def fy_year_options():
    year = datetime.today().year
    return [{"label": f"FY {year+i}", "value": year+i} for i in range(-1, 2)]

# ---------------- LAYOUT ---------------- #
layout = dbc.Container([

    # ================= EVENT ENTRY ================= #
    dbc.Card([
        dbc.CardHeader(html.H4("Upcoming Event Entry")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Title of Event *"),
                    dbc.Input(id="event-title", type="text")
                ], md=4),

                dbc.Col([
                    dbc.Label("Date of Event *"),
                    dcc.DatePickerSingle(
                        id="event-date",
                        date=datetime.today().date(),
                        display_format="DD-MM-YYYY"
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("Upload Event Image *"),
                    dcc.Upload(
                        id="event-image",
                        children=dbc.Button("Select Image"),
                        accept="image/*"
                    ),
                    html.Div(id="event-img-msg", className="text-success small")
                ], md=3),

                dbc.Col([
                    dbc.Label(" "),
                    dbc.Button("Save Event", id="save-event", color="success", className="w-100 mt-2")
                ], md=2)
            ]),
            html.Div(id="save-msg")
        ])
    ], className="shadow border card-hover",
    style={"marginBottom": "300px"}),

    # ================= TRAINING ENTRY ================= #
    dbc.Card([
        dbc.CardHeader(html.H4("Training Entry (Monthly)")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Month"),
                    dcc.Dropdown(
                        id="training-month",
                        options=month_options(),
                        value=datetime.today().month
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("Year"),
                    dbc.Input(
                        id="training-year",
                        type="number",
                        value=datetime.today().year
                    )
                ], md=2),

                dbc.Col([
                    dbc.Label("Upload Training Image"),
                    dcc.Upload(
                        id="training-image",
                        children=dbc.Button("Select Image"),
                        accept="image/*"
                    ),
                    html.Div(id="training-img-msg", className="text-success small")
                ], md=4),

                dbc.Col([
                    dbc.Label(" "),
                    dbc.Button("Upload", id="upload-training", color="primary", className="w-100 mt-2")
                ], md=3),
            ]),
            html.Div(id="training-save-msg")
        ])
    ], className="shadow border card-hover section-gap"),

    # ================= NEWSLETTER ENTRY ================= #
    dbc.Card([
        dbc.CardHeader(html.H4("Newsletter Entry (Quarterly – FY)")),
        dbc.CardBody([
            dbc.Row([
                dbc.Col([
                    dbc.Label("Quarter"),
                    dcc.Dropdown(
                        id="newsletter-quarter",
                        options=[
                            {"label": "First Quarter", "value": "first"},
                            {"label": "Second Quarter", "value": "second"},
                            {"label": "Third Quarter", "value": "third"},
                            {"label": "Fourth Quarter", "value": "fourth"},
                        ]
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("FY Year"),
                    dcc.Dropdown(
                        id="newsletter-year",
                        options=fy_year_options(),
                        value=datetime.today().year
                    )
                ], md=3),

                dbc.Col([
                    dbc.Label("Upload Newsletter Here"),
                    dcc.Upload(
                        id="newsletter-image",
                        children=dbc.Button("Select PDF", color="secondary"),
                        accept=".pdf",
                        multiple=False
                    ),
                    html.Div(id="newsletter-img-msg", className="text-success small")
                ], md=4),

                dbc.Col([
                    dbc.Label(" "),
                    dbc.Button("Upload", id="upload-newsletter", color="primary", className="w-100 mt-2")
                ], md=2),
            ]),
            html.Div(id="newsletter-save-msg")
        ])
    ], className="shadow border")

], fluid=True, className="page-fade")

# ---------------- FILE SELECT MESSAGES ---------------- #
@app.callback(Output("training-img-msg", "children"), Input("training-image", "filename"))
def show_training_file(name):
    return f"✔ Selected: {name}" if name else ""

@app.callback(Output("newsletter-img-msg", "children"), Input("newsletter-image", "filename"))
def show_newsletter_file(name):
    return f"✔ Selected: {name}" if name else ""

# ---------------- TRAINING CALLBACK ---------------- #
@app.callback(
    Output("training-save-msg", "children"),
    Input("upload-training", "n_clicks"),
    State("training-month", "value"),
    State("training-year", "value"),
    State("training-image", "contents"),
    State("training-image", "filename"),
    prevent_initial_call=True
)
def save_training(_, month, year, contents, filename):
    if not all([month, year, contents, filename]):
        return dbc.Alert("❌ All fields required", color="danger")

    ext = filename.split(".")[-1]
    month_name = datetime(2000, month, 1).strftime("%B").lower()
    file_name = f"{month_name}{year}.{ext}"

    save_image(contents, os.path.join(TRAINING_FOLDER, file_name))
    return dbc.Alert("✅ Training image saved successfully", color="success")

# ---------------- NEWSLETTER CALLBACK ---------------- #
@app.callback(
    Output("newsletter-save-msg", "children"),
    Input("upload-newsletter", "n_clicks"),
    State("newsletter-quarter", "value"),
    State("newsletter-year", "value"),
    State("newsletter-image", "contents"),
    State("newsletter-image", "filename"),
    prevent_initial_call=True
)
def save_newsletter(_, quarter, year, contents, filename):

    if not all([quarter, year, contents, filename]):
        return dbc.Alert("❌ All fields required", color="danger")

    if not filename.lower().endswith(".pdf"):
        return dbc.Alert("❌ Only PDF files are allowed", color="danger")

    file_name = f"{quarter}{year}.pdf"
    file_path = os.path.join(NEWSLETTER_FOLDER, file_name)

    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    with open(file_path, "wb") as f:
        f.write(decoded)

    return dbc.Alert("✅ Newsletter PDF uploaded successfully", color="success")



@app.callback(
    Output("event-img-msg", "children"),
    Input("event-image", "filename"),
    prevent_initial_call=True
)
def show_selected_image(filename):
    if filename:
        return f"✔ Image selected: {filename}"
    return ""



# ---------------- CALLBACK ---------------- #
@app.callback(
    Output("save-msg", "children"),
    Input("save-event", "n_clicks"),
    State("event-title", "value"),
    State("event-date", "date"),
    State("event-image", "contents"),
    State("event-image", "filename"),
    prevent_initial_call=True
)
def save_event(n_clicks, title, event_date, image_contents, image_filename):

    if not all([title, event_date, image_contents, image_filename]):
        return dbc.Alert("❌ All fields are mandatory", color="danger")

    try:
        # Dates
        entry_date = datetime.today().strftime("%d-%m-%Y")
        event_date_fmt = datetime.strptime(event_date, "%Y-%m-%d").strftime("%d-%m-%Y")

        # Image name
        ext = image_filename.split(".")[-1]
        image_name = get_next_image_name(ext)
        image_path = os.path.join(EVENT_FOLDER, image_name)

        # Save image
        save_image(image_contents, image_path)

        # Save CSV
        df = pd.read_csv(CSV_FILE)
        df.loc[len(df)] = [
            entry_date,
            title,
            event_date_fmt,
            image_name
        ]
        df.to_csv(CSV_FILE, index=False)

        return dbc.Alert("✅ Event saved successfully", color="success")

    except Exception as e:
        return dbc.Alert(f"❌ Error: {str(e)}", color="danger")
