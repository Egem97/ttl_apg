
import dash
import pandas as pd
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State, no_update
from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
import base64
import io
import qrcode
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

dash.register_page(__name__, "/packing/qr_generator", title=PAGE_TITLE_PREFIX + "Generador QR")

PAGE_ID = "qr_generator-"

def create_custom_layout():
    return dmc.Container(children=[
        Row([
            Column([
                dmc.Title("Generador PDF de QRs (3x3)", order=2, mb=20)
            ], size=12)
        ]),
        
        Row([
            Column([
                dmc.Text("1. Carga tu archivo Excel:", mb=5),
                dcc.Upload(
                    id='upload-data',
                    children=html.Div([
                        'Arrastra y suelta o ',
                        html.A('Selecciona un Archivo Excel')
                    ]),
                    style={
                        'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'marginBottom': '20px'
                    },
                    multiple=False
                ),
            ], size=12)
        ]),

        Row([
            Column([
                dmc.Text("2. Selecciona la columna para los QRs:", mb=5),
                dmc.Select(
                    id="column-selector",
                    placeholder="Primero carga un archivo...",
                    data=[],
                    disabled=True,
                    style={"width": "100%"}
                ),
            ], size=6),
            
            Column([
                 dmc.Text("3. Generar:",  mb=5),
                 dmc.Button(
                    "Generar PDF", 
                    id="btn-generate-pdf", 
                    disabled=True,
                    fullWidth=True
                ),
            ], size=6)
        ]),

        Row([
            Column([
                html.Div(id='output-status', style={'marginTop': '20px'}),
                dcc.Download(id="download-pdf-qr"),
                dcc.Store(id="stored-dataframe-json"),
            ], size=12)
        ])

    ], fluid=True)

layout = create_custom_layout()


@callback(
    Output("stored-dataframe-json", "data"),
    Output("column-selector", "data"),
    Output("column-selector", "disabled"),
    Output("output-status", "children"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    prevent_initial_call=True
)
def parse_upload_contents(contents, filename):
    if contents is None:
        return no_update, no_update, True, ""
    
    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        
        if 'xls' in filename:
            # Assume excel
            df = pd.read_excel(io.BytesIO(decoded))
            
            # Prepare options for Select
            options = [{"label": str(col), "value": str(col)} for col in df.columns]
            
            # Store dataframe as json
            # Using date_format='iso' to avoid timestamp issues
            return df.to_json(orient='split', date_format='iso'), options, False, dmc.Alert(f"Archivo cargado: {filename}. Seleccione una columna.", color="green")
        
        else:
            return no_update, no_update, True, dmc.Alert("Por favor sube un archivo Excel (.xlsx, .xls)", color="red")

    except Exception as e:
        return no_update, no_update, True, dmc.Alert(f"Error procesando archivo: {str(e)}", color="red")


@callback(
    Output("btn-generate-pdf", "disabled"),
    Input("column-selector", "value"),
    prevent_initial_call=True
)
def enable_button(value):
    return value is None


@callback(
    Output("download-pdf-qr", "data"),
    Input("btn-generate-pdf", "n_clicks"),
    State("stored-dataframe-json", "data"),
    State("column-selector", "value"),
    prevent_initial_call=True
)
def generate_qr_pdf(n_clicks, json_data, selected_column):
    if not n_clicks or not json_data or not selected_column:
        return no_update
    
    try:
        # Reconstruct DataFrame
        df = pd.read_json(io.StringIO(json_data), orient='split')
        
        if selected_column not in df.columns:
            return no_update
        
        # Get codes, ensuring they are strings and dropping NaNs if any
        codes = df[selected_column].dropna().astype(str).tolist()
        
        # Create PDF
        buffer = io.BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # 3x3 Grid Config
        cols = 3
        rows = 3
        
        # Grid dimensions
        margin_x = 10 * mm
        margin_y = 10 * mm
        
        available_width = width - (2 * margin_x)
        available_height = height - (2 * margin_y)
        
        cell_width = available_width / cols
        cell_height = available_height / rows
        
        items_per_page = cols * rows
        
        for i, code in enumerate(codes):
            # Calculate position on current page
            page_index = i % items_per_page
            
            col_idx = page_index % cols
            # Top row is index 0 visually, but in reportlab y increases upwards.
            # So row 0 (top) is actually at the highest y.
            # Let's map row_idx 0 to top, row_idx 2 to bottom.
            visual_row = page_index // cols
            
            # Start from top: height - margin_y - cell_height * (visual_row + 1)
            y_pos = height - margin_y - (cell_height * (visual_row + 1))
            x_pos = margin_x + (col_idx * cell_width)
            
            # Center of the cell
            center_x = x_pos + (cell_width / 2)
            center_y = y_pos + (cell_height / 2)
            
            # QR Code Generation
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=2,
            )
            qr.add_data(code)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert PIL image to bytes
            img_buffer = io.BytesIO()
            img.save(img_buffer, format="PNG")
            img_buffer.seek(0)
            
            # Image dimensions
            qr_size = 50 * mm 
            
            # Draw QR Image (centered in cell, slightly moved up)
            # Center of image should be at (center_x, center_y + offset)
            # Bottom-left of image:
            qr_bottom_left_x = center_x - (qr_size / 2)
            qr_bottom_left_y = center_y - (qr_size / 2) + (5 * mm)
            
            c.drawImage(ImageReader(img_buffer), qr_bottom_left_x, qr_bottom_left_y, width=qr_size, height=qr_size)
            
            # Draw Text
            c.setFont("Helvetica", 12)
            # Text below image
            c.drawCentredString(center_x, qr_bottom_left_y - (5 * mm), code)
            
            # Optional: Draw cell border for debugging/cutting guide
            # c.setStrokeColorRGB(0.8, 0.8, 0.8)
            # c.rect(x_pos, y_pos, cell_width, cell_height)
            
            # New Page if filled or last item
            if (i + 1) % items_per_page == 0:
                c.showPage()
            elif (i + 1) == len(codes):
                # Don't add a blank page if it fits exactly, but showPage() saves the current page.
                # If we just finished the loop and didn't hit the modulo, we need to save the page.
                c.showPage()
                
        c.save()
        buffer.seek(0)
        
        return dcc.send_bytes(buffer.getvalue(), "codigos_qr.pdf")

    except Exception as e:
        # In case of error during generation, we can't easily return an alert to a dcc.Download component
        # But we could print it or handle it if we had a separate output.
        # For now, just fail silently or return nothing (files might be missing lib dependencies if not installed)
        print(f"Error creating PDF: {e}")
        return no_update