import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import os

from app import app
import pandas as pd
from datetime import datetime

EVENT_CSV = "assets/events/data.csv"

def load_events():
    df = pd.read_csv(EVENT_CSV)

    df["Heading"] = df["Heading"].astype(str).str.strip()
    df["image"] = df["image"].astype(str).str.strip()
    df["eventdate"] = pd.to_datetime(
        df["eventdate"], dayfirst=True, errors="coerce"
    )

    return df



def today():
    return pd.Timestamp.now().normalize()

# Function to list files in specified folder
def list_photos():
    photos_path = os.path.join(os.getcwd(), 'assets', 'images')
    photos = [f for f in os.listdir(photos_path) if os.path.isfile(os.path.join(photos_path, f))]
    return photos

# Dynamically generate items for the photo carousel
def generate_carousel_items():
    photos = list_photos()
    carousel_items = []
    for idx, photo in enumerate(photos):
        carousel_items.append(
            {"key": str(idx), "src": f"./assets/images/{photo}", "img_style": {'max-width': '100%', 'height': '80vh',
                                                                               "max-height": "1200px",
                                                                               'border-radius': '20px'}}
        )
    return carousel_items

# Background image with blur effect
background = html.Div(
    style={
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'width': '100%',
        'height': '100%',
        'z-index': -1,
       # 'background-image': 'url("/assets/background.jpg")',
        'background-size': 'cover',
        'filter': 'brightness(85%) blur(5px)',
        'pointer-events': 'none'  # <-- FIX HERE
    }
)


carousel = html.Div(
    [
        dcc.Interval(
            id='refresh-interval',
            interval=10 * 1000,
            n_intervals=0
        ),
        dbc.Carousel(
            id='photo-carousel',
            items=generate_carousel_items(),
            controls=True,
            interval=2000,
            variant="dark",
            style={
                'margin': '10px 20px',
                'padding': '10px 0'
            }
        )
    ],
    style={
        'position': 'relative',
        'zIndex': 1,
        'paddingTop': '10px'   # 🔥 WAS 160px
    }
)

def upcoming_events_box():
    df = load_events()
    upcoming = df[df["eventdate"] >= today()].sort_values("eventdate")

    return html.Div(
        [
            html.H5("Upcoming Events", className="mb-2"),
            html.Div(
                [
                    dcc.Link(
                        html.Div(
                            e["Heading"],
                            className="event-item"
                        ),
                        href=f"/events?name={e['Heading']}"
                    )
                    for _, e in upcoming.iterrows()
                ],
                style={
                    "maxHeight": "70vh",
                    "overflowY": "auto"
                }
            )
        ],
          style={
                                "maxHeight": "85vh",
                                "overflowY": "auto",
                                "display": "flex",
                                "flexWrap": "wrap",
                                "gap": "15px",
                                "padding": "10px"
                            }

    )


# Layout combining background and carousel
layout = html.Div(
    [
        background,

        dbc.Container(
            dbc.Row(
                [
                    # Horizontal redirect tabs
                    dbc.Col(
                        html.Div(
                            [
                                html.A(
                                    "jkc digital library",
                                    href="https://jkcdigitallibrary.jsw.in/home",
                                    target="_blank",
                                    className="custom-tab-button"
                                ),
                                html.A(
                                    "TQM",
                                    href="https://tqm.jsw.in/TQM/tqmHome.action;jsessionid=A3FCA55A1D579F18E340C3B02BBDB32E",
                                    target="_blank",
                                    className="custom-tab-button"
                                ),
                                html.A(
                                    "TMS",
                                    href="https://tms.jsw.in/TQM/jsw/auth/login.do",
                                    target="_blank",
                                    className="custom-tab-button"
                                ),
                                 html.A(
                                    "J1 lite",
                                    href="http://10.10.20.208:2221/",
                                    target="_blank",
                                    className="custom-tab-button"
                                ),

                            ],
                            className="custom-tabs-container"
                        ),
                        md=12,
                        style={"paddingBottom": "20px"}
                    ),

                    # 🔥 TOP: UPCOMING EVENTS
                    dbc.Col(
                        html.Div(id="upcoming-events-container"),
                        md=12,
                        style={"paddingBottom": "15px"}
                    ),


                    # 🔥 BOTTOM: IMAGE / CAROUSEL
                    dbc.Col(
                        carousel,
                        md=12,
                    )
                ],
                className="g-0",
                align="start"
            ),
            fluid=True
        )
    ]
)





# Callback to update the photo carousel content periodically
@app.callback(
    Output('photo-carousel', 'items'),
    Input('refresh-interval', 'n_intervals')
)
def update_carousel(n):
    return generate_carousel_items()

def event_color(idx):
    colors = ["green", "gray", "orange", "blue", "gold"]
    return colors[idx % len(colors)]


@app.callback(
    Output("upcoming-events-container", "children"),
    Input("refresh-interval", "n_intervals")
)
def update_upcoming_events(n):
    df = load_events()

    if df.empty:
        return None

    today_date = pd.Timestamp.now().normalize()
    upcoming = df[df["eventdate"] >= today_date].sort_values("eventdate")

    if upcoming.empty:
        return None

    return html.Div(
        [
            html.Div(
                "UPCOMING EVENTS", 
                className="events-title-horizontal"
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
                    for idx, (_, e) in enumerate(upcoming.iterrows())
                ],
                style={
                    "maxHeight": "75vh",
                    "overflowY": "auto",
                    "paddingRight": "6px"
                }
            )
        ],
        className="events-panel"
    )
