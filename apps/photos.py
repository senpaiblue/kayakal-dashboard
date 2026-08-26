import os
import base64
from dash import html, dcc, Input, Output, State, ALL
from app import app
import dash_bootstrap_components as dbc
from dash.exceptions import PreventUpdate

# Function to list files in the specified folder
def list_photos():
    photos_path = os.path.join(os.getcwd(), 'assets', 'images')
    photos = [f for f in os.listdir(photos_path) if os.path.isfile(os.path.join(photos_path, f))]
    return photos

def generate_carousel_items():
    photos = list_photos()
    carousel_items = []
    for idx, photo in enumerate(photos):
        carousel_items.append(
            dbc.CarouselItem(
                html.Div([
                    html.Img(src=f"./assets/images/{photo}", style={'max-width': '100%', 'height': '80vh', 'max-height': '1200px', 'border-radius': '20px'}),
                ]),
                key=f"carousel-item-{idx}"
            )
        )
    return carousel_items
# Layout for the photos page
layout = html.Div([
    dcc.Upload(
        id='upload-image',
        children=html.Div([
            'Drag and Drop or ',
            html.A('Select Files')
        ]),
        style={
            'width': '100%',
            'height': '60px',
            'lineHeight': '60px',
            'borderWidth': '1px',
            'borderStyle': 'dashed',
            'borderRadius': '5px',
            'textAlign': 'center',
            'margin': '10px 0'
        },
        # Allow multiple files to be uploaded
        multiple=True
    ),
    html.Div(id='output-image-upload'),
    html.Button("Show Photos", id="show-photos-button", style={'margin': '10px 0'}),
    html.Div(id='output-photos'),
    html.Button("Delete Selected", id="delete-selected-button", style={'margin': '10px 0'}),
    html.Div(id='delete-status')
])

@app.callback(Output('output-image-upload', 'children'),
              Input('upload-image', 'contents'),
              State('upload-image', 'filename'))
def update_output(contents, filenames):
    if contents is not None:
        for content, name in zip(contents, filenames):
            # Decode base64 content
            content_type, content_string = content.split(',')
            decoded = base64.b64decode(content_string)

            # Write to file
            with open(os.path.join('assets', 'images', name), 'wb') as f:
                f.write(decoded)

        return html.Div([
            html.P(f'{name} uploaded successfully!') for name in filenames
        ])

# Callback to display photos as thumbnails
@app.callback(Output('output-photos', 'children'),
              [Input('show-photos-button', 'n_clicks'),
               Input('upload-image', 'contents')],
              [State('upload-image', 'filename')])
def display_photos(n_clicks, list_of_contents, list_of_names):
    print("Callback triggered")
    if n_clicks is None:
        return ""

    photos = list_photos()

    if not photos:
        return html.P("No photos available.")

    photos_path = os.path.join(os.getcwd(), 'assets', 'images')
    photo_elements = [
        html.Div([
            html.Img(src=f"/assets/images/{photo}", style={'width': '100px', 'margin': '5px'}),
            dcc.Checklist(id={'type': 'photo-checkbox', 'index': i}, options=[{'label': photo, 'value': photo}], style={'margin': '5px'})
        ]) 
        for i, photo in enumerate(photos)
    ]

    return html.Div([
        html.P("Photos:"),
        html.Div(photo_elements)
    ])

# Callback to delete selected photos
@app.callback(Output('delete-status', 'children'),
              Input('delete-selected-button', 'n_clicks'),
              [State({'type': 'photo-checkbox', 'index': ALL}, 'value')])
def delete_selected_photos(n_clicks, checked_values):
    print("Delete callback triggered")
    print("Checked values:", checked_values)
    
    if n_clicks is None:
        return ""

    if not any(checked_values):
        return html.P("No photos selected for deletion.")

    photos_path = os.path.join(os.getcwd(), 'assets', 'images')
    photos = list_photos()
    deleted_photos = []

    for i, checked in enumerate(checked_values):
        if checked:
            photo_to_delete = photos[i]
            photo_path = os.path.join(photos_path, photo_to_delete)
            print("Deleting photo:", photo_path)
            os.remove(photo_path)
            deleted_photos.append(photo_to_delete)

    if deleted_photos:
        return html.P(f"Selected photos ({', '.join(deleted_photos)}) deleted successfully.")
    else:
        return html.P("No photos selected for deletion.")

if __name__ == '__main__':
    app.run_server(debug=False)
