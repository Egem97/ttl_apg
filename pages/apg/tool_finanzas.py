import dash
import pandas as pd
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month
from dash_ag_grid import AgGrid
from helpers.get_sheets import read_sheet
import base64
import io
import pytz
import zipfile
from datetime import datetime, timedelta, time
import re

# 🚀 Configuraciones de rendimiento optimizadas
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
pd.options.mode.sim_interactive = True  # Optimizar para operaciones interactivas

dash.register_page(__name__, "/apg/txt_detracciones", title=PAGE_TITLE_PREFIX + "TXT Detracciones")
app = dash.get_app()
PAGE_ID = "tool_finanzas-"
DATA_SOURCE = "tool_finanzas"


def create_custom_layout():
    return dmc.Container(children=[
        Row([
            Column([
                dmc.Title("Transformacion TXT Detracciones")
            ], size=6),
            Column([
                dcc.Upload(
                    id='upload-data-finanzas',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        #'width': '100%',
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    # Allow multiple files to be uploaded
                    multiple=True
                ),
               
            ], size=6)
        ]),
        Row([
            Column([
                dmc.Textarea(
                    id="preview-area-finanzas",
                    label="Vista previa (Primeras 5 líneas del último archivo)",
                    autosize=True,
                    minRows=5,
                    maxRows=10,
                    #readonly=True,
                    style={"fontFamily": "monospace"}
                ),
                html.Div(id='output-status-finanzas', style={'marginTop': '10px'})
            ])
        ]),
        Row([
            Column([
                dmc.Group([
                    dmc.Button("Descargar Procesados (.txt/.zip)", id="btn-download-finanzas"),
                    dcc.Download(id="download-dataframe-xlsx-finanzas"),
                    dcc.Store(id="finanzas-store"),
                ], mb=10),
                
            ])
        ])
    ], fluid=True)

layout = create_custom_layout()

def get_batch_code():
    # Obtener fecha actual en Perú -> YYMMDD
    tz = pytz.timezone('America/Lima')
    return datetime.now(tz).strftime('%y%m%d')

def transform_line(line, line_idx, batch_code):
    # Remove newlines for easier handling
    clean_line = line.strip('\r\n')
    
    # Lógica para Cabecera 
    if clean_line.startswith('*'):
        if len(clean_line) >= 53:
            new_header = clean_line[:47] + batch_code + clean_line[53:]
            return new_header + '\r\n'
        return clean_line + '\r\n'
        
    # Lógica para Detalle
    # Actualización: Cambiar el caracter 0 por 1 en la posición -21 (justo antes de la fecha)
    # Nota: Se mantiene la longitud total de la línea.
    if len(clean_line) > 21:
        clean_line = clean_line[:-21] + '1' + clean_line[-20:]

    return clean_line + '\r\n'

def generate_filename(header_line, batch_code):
    # User Request: D + RUC + periodo(lote), ejemplo D20612997285260123
    # Header Start: *
    # RUC: Pos 1-12 (11 chars)
    try:
        if header_line.startswith('*'):
             ruc = header_line[1:12]
             return f"D{ruc}{batch_code}.txt"
        return f"salida_{batch_code}.txt"
    except:
        return f"salida_{batch_code}.txt"

def process_file_content(content_string, original_filename, batch_code):
    try:
        # Check if contents has the header (data:text/plain;base64,...)
        if ',' in content_string:
            content_type, content_string = content_string.split(',')
            
        decoded = base64.b64decode(content_string)
        # Decode as utf-8-sig to verify BOM, fallback to latin-1
        try:
            text_content = decoded.decode('utf-8-sig')
        except UnicodeDecodeError:
            text_content = decoded.decode('latin-1')
            
        stringio = io.StringIO(text_content)
        lines = stringio.readlines()
        
        output_lines = []
        new_filename = f"processed_{original_filename}"
        
        for idx, line in enumerate(lines):
            # Asumimos primera línea es cabecera para el nombre
            if idx == 0 and line.strip().startswith('*'):
                new_filename = generate_filename(line, batch_code)
            
            transformed = transform_line(line, idx, batch_code)
            output_lines.append(transformed)
            
        return new_filename, "".join(output_lines)
    except Exception as e:
        print(f"Error processing {original_filename}: {e}")
        return None, None

@callback(
    Output('preview-area-finanzas', 'value'),
    Output('output-status-finanzas', 'children'),
    Output('finanzas-store', 'data'),
    Input('upload-data-finanzas', 'contents'),
    State('upload-data-finanzas', 'filename'),
)
def update_output(list_of_contents, list_of_names):
    if list_of_contents is None:
        return "", "", None
    
    batch_code = get_batch_code()
    processed_files = []
    last_preview = ""
    
    for c, n in zip(list_of_contents, list_of_names):
        new_name, content = process_file_content(c, n, batch_code)
        if new_name and content:
            processed_files.append({
                "filename": new_name,
                "content": content
            })
            # Preview first 5 lines of the last processed file
            last_preview = "".join(content.splitlines(keepends=True)[:5])
            
    if not processed_files:
        return "Error procesando archivos.", dmc.Alert("No se pudieron procesar los archivos.", color="red"), None
        
    msg = f"Se han procesado {len(processed_files)} archivos correctamente. Lote: {batch_code}"
    return last_preview, dmc.Alert(msg, color="green"), processed_files

@callback(
    Output("download-dataframe-xlsx-finanzas", "data"),
    Input("btn-download-finanzas", "n_clicks"),
    State("finanzas-store", "data"),
    prevent_initial_call=True,
)
def download_files(n_clicks, data):
    if not data:
        return None
    
    # data is a list of dicts: [{'filename': '...', 'content': '...'}]
    
    if len(data) == 1:
        # Single file download
        file_data = data[0]
        return dict(content=file_data['content'], filename=file_data['filename'])
    else:
        # Zip download
        output_zip = io.BytesIO()
        with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            for item in data:
                zf.writestr(item['filename'], item['content'])
        
        output_zip.seek(0)
        return dcc.send_bytes(output_zip.read(), filename=f"detracciones_procesadas_{len(data)}.zip")