import dash_bootstrap_components as dbc
from dash import html, dcc, Input, Output
import os

from app import app

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


carousel = html.Div([
    dcc.Interval(
        id='refresh-interval',
        interval=10*1000,
        n_intervals=0
    ),
    dbc.Carousel(
        id='photo-carousel',
        items=generate_carousel_items(),
        controls=True,
        interval=2000,
        variant="dark",
        style={'margin': '20px 100px', 'padding': '50px 0'}
    )
], style={
    'position': 'relative',
    'zIndex': 1,
    'paddingTop': '160px'
})


# Layout combining background and carousel
layout = html.Div([background, carousel])

# Callback to update the photo carousel content periodically
@app.callback(
    Output('photo-carousel', 'items'),
    Input('refresh-interval', 'n_intervals')
)
def update_carousel(n):
    return generate_carousel_items()
