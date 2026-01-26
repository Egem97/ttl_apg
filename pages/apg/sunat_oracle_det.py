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

dash.register_page(__name__, "/apg/sunat_oracle_det", title=PAGE_TITLE_PREFIX + "Sunat Oracle Det")
app = dash.get_app()
PAGE_ID = "sunat_oracle_det-"
DATA_SOURCE = "sunat_oracle_det"


def parse_sunat_txt(content):
    """
    Parse SUNAT SPOT TXT file and extract header and detail information.
    
    Returns:
        tuple: (header_dict, details_list)
    """
    try:
        # Decode content
        decoded = base64.b64decode(content)
        text = decoded.decode('utf-8')
    except:
        try:
            text = decoded.decode('latin-1')
        except:
            return None, None
    
    lines = text.split('\n')
    header_data = {}
    details_data = []
    current_detail = {}
    
    in_header_section = False
    in_detail_section = False
    
    # Pattern to match lines with field names and values separated by multiple spaces
    # Format: "Field Name                    Value"
    field_pattern = re.compile(r'^(.+?)\s{2,}(.+)$')
    
    for line in lines:
        original_line = line
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
        
        # Detect sections
        if 'Datos de cabecera' in line:
            in_header_section = True
            in_detail_section = False
            continue
        elif 'Datos de detalle' in line:
            in_header_section = False
            in_detail_section = True
            continue
        
        # Skip title lines
        if 'SISTEMA DE PAGO' in line or 'CONSTANCIA DE DEPOSITO' in line:
            continue
        
        # Parse header data
        if in_header_section:
            match = field_pattern.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                header_data[key] = value
        
        # Parse detail data
        if in_detail_section:
            match = field_pattern.match(line)
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                
                # Check if this is a new detail record
                if key == 'Número de constancia':
                    # Save previous detail if exists
                    if current_detail:
                        details_data.append(current_detail)
                    current_detail = {}
                
                # Add field to current detail
                current_detail[key] = value
    
    # Add last detail
    if current_detail:
        details_data.append(current_detail)
    
    return header_data, details_data


def create_custom_layout():
    return dmc.Container(children=[
        Row([
            Column([
                dmc.Title("Matching Sunat Oracle Det")
            ], size=12),
            
        ]),
        Row([
            Column([
                dmc.Text("Archivo SUNAT SPOT:", fw=500, size="sm", mb=5),
                dcc.Upload(
                    id='upload-data-txt',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    multiple=False
                ),
               
            ], size=6),
            Column([
                dmc.Text("Archivo Oracle:", fw=500, size="sm", mb=5),
                dcc.Upload(
                    id='upload-data-oracle',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select Files')
                    ]),
                    style={
                        'height': '60px',
                        'lineHeight': '60px',
                        'borderWidth': '1px',
                        'borderStyle': 'dashed',
                        'borderRadius': '5px',
                        'textAlign': 'center',
                        'margin': '10px'
                    },
                    multiple=False
                ),
               
            ], size=6)
        ]),
        
        # Header Information Section
        Row([
            Column([
                html.Div(id='sunat-header-info', style={'marginTop': '20px'})
            ], size=12)
        ]),
        
        # Detail Data Table Section
        Row([
            Column([
                html.Div(id='sunat-detail-table', style={'marginTop': '20px'})
            ], size=12)
        ]),
        
        Row([
            Column([
                dmc.Group([
                    dmc.Button("Descargar Procesados (.txt/.zip)", id="btn-download-sunat_oracle_det"),
                    dcc.Download(id="download-dataframe-xlsx-sunat_oracle_det"),
                    dcc.Store(id="sunat_oracle_det-store"),
                ], mb=10),
                
            ])
        ])
    ], fluid=True)

layout = create_custom_layout()


# Callback to process uploaded SUNAT TXT file
@callback(
    [Output('sunat-header-info', 'children'),
     Output('sunat-detail-table', 'children'),
     Output('sunat_oracle_det-store', 'data')],
    [Input('upload-data-txt', 'contents')],
    [State('upload-data-txt', 'filename')]
)
def process_sunat_file(contents, filename):
    if contents is None:
        return None, None, None
    
    # Parse the file
    content_string = contents.split(',')[1]
    header_data, details_data = parse_sunat_txt(content_string)
    
    if header_data is None or details_data is None:
        return dmc.Alert("Error al procesar el archivo", color="red"), None, None
    
    # Create header display
    header_display = dmc.Card([
        dmc.Title("SISTEMA DE PAGO DE OBLIGACIONES TRIBUTARIAS (SPOT)", order=4, mb=10),
        dmc.Title("CONSTANCIA DE DEPOSITO MASIVO", order=5, mb=20, c="dimmed"),
        dmc.Divider(mb=15),
        dmc.Title("Datos de Cabecera", order=5, mb=15),
        dmc.Grid([
            dmc.GridCol([
                dmc.Text("Número de operación:", fw=600, size="sm"),
                dmc.Text(header_data.get('Número de operación', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Fecha y hora de pago:", fw=600, size="sm"),
                dmc.Text(header_data.get('Fecha y hora de pago', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Archivo:", fw=600, size="sm"),
                dmc.Text(header_data.get('Archivo', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Lote:", fw=600, size="sm"),
                dmc.Text(header_data.get('Lote', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("RUC del Adquiriente:", fw=600, size="sm"),
                dmc.Text(header_data.get('RUC del Adquiriente', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Razón Social del Adquiriente:", fw=600, size="sm"),
                dmc.Text(header_data.get('Razón Social del Adquiriente', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Número de depósitos:", fw=600, size="sm"),
                dmc.Text(header_data.get('Número de depósitos', 'N/A'), size="sm", mb=10)
            ], span=6),
            dmc.GridCol([
                dmc.Text("Monto total:", fw=600, size="sm"),
                dmc.Text(header_data.get('Monto total', 'N/A'), size="sm", mb=10)
            ], span=6),
        ])
    ], withBorder=True, shadow="sm", p="lg", mb=20)
    
    # Create DataFrame from details
    if details_data:
        df = pd.DataFrame(details_data)
        
        # Create AgGrid table
        detail_table = html.Div([
            dmc.Title("Datos de Detalle", order=5, mb=15),
            AgGrid(
                id='sunat-detail-grid',
                rowData=df.to_dict('records'),
                columnDefs=[{"field": col, "filter": True, "sortable": True, "resizable": True} for col in df.columns],
                columnSize="sizeToFit",
                dashGridOptions={
                
                "animateRows": True,
                #"pagination": True,
                #"paginationPageSize": 20,
                "defaultColDef": {
                    #"sortable": True,
                    #"filter": True,
                    "resizable": True,
                    "minWidth": 120
                }
            },
                style={"height": "400px"},
            )
        ])
        
        # Store data for later use
        store_data = {
            'header': header_data,
            'details': details_data
        }
        
        return header_display, detail_table, store_data
    else:
        return header_display, dmc.Alert("No se encontraron datos de detalle", color="yellow"), {'header': header_data, 'details': []}
