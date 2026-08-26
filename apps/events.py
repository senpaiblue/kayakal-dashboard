from dash import html, dcc
from dash.dependencies import Input, Output
import dash_bootstrap_components as dbc
import pandas as pd
from urllib.parse import unquote
import os

from app import app

# ========================
# PATHS (FIXED)
# ========================
EVENT_CSV = "assets/events/data.csv"
EVENT_IMG_DIR = "assets/events"

# ========================
# LOAD EVENTS (FIXED)
# ========================
def load_events():
    df = pd.read_csv(EVENT_CSV)

    # 🔥 CRITICAL FIXES
    df["Heading"] = df["Heading"].astype(str).str.strip()
    df["image"] = df["image"].astype(str).str.strip()
    df["eventdate"] = pd.to_datetime(df["eventdate"], dayfirst=True, errors="coerce")

    return df

# ========================
# PAGE LAYOUT (MUST BE VARIABLE)
# ========================
layout = html.Div(
    [
        dcc.Location(id="event-url", refresh=False),
        html.Div(id="event-content", style={"padding": "20px"})
    ]
)
def event_color(idx):
    colors = ["green", "gray", "orange", "blue", "gold"]
    return colors[idx % len(colors)]

# ========================
# CALLBACK
# ========================
@app.callback(
    Output("event-content", "children"),
    Input("event-url", "search")
)
def load_event(search):
    df = load_events()

    # ========================
    # DEFAULT IMAGE → LATEST EVENTDATE
    # ========================
    latest_event = df.sort_values("eventdate", ascending=False).iloc[0]
    img_src = f"/assets/events/{latest_event['image']}"

    # ========================
    # SELECTED EVENT
    # ========================
    if search and "name=" in search:
        event_name = unquote(search.split("name=")[1]).strip()

        row = df[df["Heading"] == event_name]
        if not row.empty:
            image_file = row.iloc[0]["image"]
            image_path = os.path.join(EVENT_IMG_DIR, image_file)

            if os.path.exists(image_path):
                img_src = f"/assets/events/{image_file}"

    # ========================
    # EVENT LIST (ALL EVENTS)
    # ========================
    all_events = df.sort_values("eventdate", ascending=False)

    return dbc.Row(
        [
            # -------- IMAGE --------
            dbc.Col(
                html.Img(
                    src=img_src,
                    style={
                        "width": "100%",
                        "height": "auto",
                        "borderRadius": "12px",
                        "objectFit": "cover"
                    }
                ),
                md=10
            ),

            # -------- EVENT LIST --------
            dbc.Col(
                html.Div(
                    [
                        html.Div(
                            "EVENTS",
                            className="events-title-vertical"
                        ),

                        html.Div(
                            [
                                dcc.Link(
                                    html.Div(
                                        [
                                            html.Div(
                                                f"{idx+1:02d}",
                                                className=f"hex {event_color(idx)}"
                                            ),
                                            html.Div(
                                                [
                                                    html.Div(
                                                        e["Heading"],
                                                        className="event-heading"
                                                    ),
                                                    html.Div(
                                                        e["eventdate"].strftime("%d %b %Y"),
                                                        className="event-date"
                                                    ),
                                                ]
                                            )
                                        ],
                                        className="event-card"
                                    ),
                                    href=f"/events?name={e['Heading']}",
                                    style={"textDecoration": "none"}
                                )
                                for idx, (_, e) in enumerate(all_events.iterrows())
                            ],
                            style={
                                "maxHeight": "85vh",
                                "overflowY": "auto",
                                "paddingRight": "6px"
                            }
                        )
                    ],
                    className="events-panel"
                ),
                md=2
            

            )
        ],
        className="g-3"
    )
