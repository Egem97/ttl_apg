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
                
                html.Div(id='sunat-header-info', style={'marginTop': '20px'}),
                html.Div(id='sunat-detail-table', style={'marginTop': '20px'})
               
            ], size=6),
            Column([
                dmc.Text("Archivo Oracle (CSV):", fw=500, size="sm", mb=5),
                dcc.Upload(
                    id='upload-data-oracle',
                    children=html.Div([
                        'Drag and Drop or ',
                        html.A('Select CSV Files')
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
                    multiple=False,
                    accept='.csv'
                ),
                html.Div(id='oracle-table', style={'marginTop': '20px'}),
                html.Div(id='oracle-upload-status', style={'marginTop': '10px'})
            ], size=6)
        ]),
        
        # Nueva sección para la tabla de matching
        Row([
            Column([
                html.Div(id='matching-table', style={'marginTop': '30px'})
            ], size=12)
        ]),
        
        Row([
            Column([
                dmc.Group([
                    dmc.Button("Descargar csv", id="btn-download-sunat_oracle_det"),
                    dcc.Download(id="download-dataframe-xlsx-sunat_oracle_det"),
                    dcc.Store(id="sunat_oracle_det-store"),
                    dcc.Store(id="sunat-data-store"),  # Store para datos de SUNAT
                    dcc.Store(id="oracle-data-store"),  # Store para datos de Oracle
                    dcc.Store(id="matching-data-store"),  # Store para datos del matching
                ], mb=10),
                
            ])
        ])
    ], fluid=True)

layout = create_custom_layout()


# Callback to process uploaded SUNAT TXT file
@callback(
    [Output('sunat-header-info', 'children'),
     Output('sunat-detail-table', 'children'),
     Output('sunat_oracle_det-store', 'data'),
     Output('sunat-data-store', 'data')],
    [Input('upload-data-txt', 'contents')],
    [State('upload-data-txt', 'filename')]
)
def process_sunat_file(contents, filename):
    if contents is None:
        return None, None, None, None
    
    # Parse the file
    content_string = contents.split(',')[1]
    header_data, details_data = parse_sunat_txt(content_string)
    
    if header_data is None or details_data is None:
        return dmc.Alert("Error al procesar el archivo", color="red"), None, None, None
    
    # Create header display
    header_display = html.Div()
    
    # Create DataFrame from details
    if details_data:
        df = pd.DataFrame(details_data)
        df["Fecha Pago"] = header_data.get('Fecha y hora de pago', 'N/A')
        df["Fecha Pago"] = pd.to_datetime(df["Fecha Pago"]).dt.strftime('%d/%m/%Y')
        
        # Crear columna factura_limpia para el matching
        # Formato: "F001 00000101" -> ya viene en el formato correcto desde SUNAT
        df['factura_limpia'] = df['Número de Comprobante']
        
        # Renombrar columna para el matching
        df = df.rename(columns={'Número Documento del Proveedor': 'ruc'})
        
        df_display = df [[
            'Número de constancia', 
       'ruc', 'Nombre/Razón Social del Proveedor',
       'Monto depósito', 'Periodo Tributario','Número de Comprobante', 'Fecha Pago'
        ]]
        # Create AgGrid table
        detail_table = html.Div([
            dmc.Title(f"Datos de Detalle - Total registros: {df.shape[0]}", order=5, mb=15),
            AgGrid(
                id='sunat-detail-grid',
                rowData=df_display.to_dict('records'),
                columnDefs=[{"field": col, "filter": True, "sortable": True, "resizable": True} for col in df_display.columns],
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
                className="ag-theme-quartz compact"
            )
        ])
        
        # Store data for later use
        store_data = {
            'header': header_data,
            'details': details_data
        }
        
        # Guardar DataFrame procesado para el matching
        sunat_data_store = df.to_dict('records')
        
        return header_display, detail_table, store_data, sunat_data_store
    else:
        return header_display, dmc.Alert("No se encontraron datos de detalle", color="yellow"), {'header': header_data, 'details': []}, None



# Callback to process uploaded Oracle CSV file
@callback(
    [Output('oracle-table', 'children'),
     Output('oracle-upload-status', 'children'),
     Output('oracle-data-store', 'data')],
    [Input('upload-data-oracle', 'contents')],
    [State('upload-data-oracle', 'filename')]
)
def process_oracle_csv(contents, filename):
        subsidiary = pd.read_excel('oracle_prod.xlsx', sheet_name='Subsidiary')
        #proveedor = pd.read_excel('oracle_prod.xlsx', sheet_name='Proveedor')
        #proveedor = proveedor.rename(columns={'altname':'name_proveedor','custentity_gd_documento':'ruc'})
        subsidiary_dict = (
            subsidiary
            .set_index('name_subsidiary')['id_subsidiary']
            .to_dict()
        )
        #proveedor_dict = (
        #    proveedor
        #    .set_index('name_proveedor')['ruc']
        #    .to_dict()
        #)
        if contents is None:
            return None, None, None
        
        # Columnas originales esperadas del CSV de Oracle
        original_columns = [
            'ID interno', 'Fecha', 'Número de documento',  'Moneda', 'Importe Pagado',
            'Factura relacionada', 'Subsidiaria','Proveedor'
        ]
    
    
        # Validate file extension
        if not filename.lower().endswith('.csv'):
            return None, dmc.Alert(
                "Error: Solo se permiten archivos CSV",
                color="red",
                title="Formato de archivo incorrecto"
            ), None
        
        # Parse the CSV file
        content_string = contents.split(',')[1]
        decoded = base64.b64decode(content_string)
        
        # Try different encodings
        try:
            text = decoded.decode('utf-8')
        except:
            try:
                text = decoded.decode('latin-1')
            except:
                return None, dmc.Alert(
                    "Error: No se pudo decodificar el archivo",
                    color="red",
                    title="Error de codificación"
                ), None
        
        # Read CSV into DataFrame
        df = pd.read_csv(io.StringIO(text))
        df = df.rename(columns={'Nombre.1':'Proveedor'})
        
        df = df[df["ID interno"].notna()]
        # Filtrar solo las columnas originales que necesitamos
        df = df[original_columns]
        df['Subsidiaria'] = df['Subsidiaria'].str.split(':').str[-1].str.strip()
        df['id_subsidiary'] = df['Subsidiaria'].map(subsidiary_dict)
        
        df['ruc'] = df['Proveedor'].str[:11]#.map(proveedor_dict)
        print("--------------------------------------")
        print(df['ruc'].unique())
        # Crear columna factura_limpia
        # Formato original: "Factura #F001-00000009"
        # Formato deseado: "F001 00000009" (serie de 4 chars + espacio + número con padding de 8 dígitos)
        df['factura_limpia'] = df['Factura relacionada'].str.replace('Factura #', '', regex=False).str.replace('-', ' ', regex=False)
        
        # Crear columnas temporales para serie y numero
        df[['serie', 'numero']] = df['factura_limpia'].str.split(' ', n=1, expand=True)
        
        # Identificar filas válidas (que tienen exactamente un espacio, es decir, serie y numero separados)
        mask_valida = df['numero'].notna()
        
        # Formatear solo las filas válidas: serie (primeros 4 caracteres) + espacio + número (padding de 8 dígitos)
        df.loc[mask_valida, 'factura_limpia'] = (
            df.loc[mask_valida, 'serie'].str[:4] + ' ' +
            df.loc[mask_valida, 'numero'].str.zfill(8)
        )
        
        # Eliminar columnas temporales
        df = df.drop(columns=['serie', 'numero'], errors='ignore')
        
        # Columnas finales esperadas (incluyendo factura_limpia)
        expected_columns = original_columns + ['factura_limpia','id_subsidiary','ruc']
        
        
        # Validate column structure
        if len(df.columns) != len(expected_columns):
            return None, dmc.Alert(
                f"Error: El archivo debe tener {len(expected_columns)} columnas. Se encontraron {len(df.columns)} columnas.",
                color="red",
                title="Estructura incorrecta"
            ), None
        
        # Check if column names match (case-insensitive)
        df_columns_lower = [col.strip().lower() for col in df.columns]
        expected_columns_lower = [col.strip().lower() for col in expected_columns]
        
        # Note: There are duplicate column names in the expected structure
        # We'll just validate the count for now
        if df.empty:
            return None, dmc.Alert(
                "El archivo CSV está vacío",
                color="yellow",
                title="Advertencia"
            ), None
        
        # Create AgGrid table
        oracle_table = html.Div([
            dmc.Title(f"Datos de Oracle - Total de registros: {len(df)}", order=5, mb=15),
          
            AgGrid(
                id='oracle-data-grid',
                rowData=df.to_dict('records'),
                columnDefs=[
                    {
                        "field": col, 
                        "filter": True, 
                        "sortable": True, 
                        "resizable": True,
                        "headerName": col
                    } for col in df.columns
                ],
                columnSize="sizeToFit",
                dashGridOptions={
                    "animateRows": True,
                    
                    "defaultColDef": {
                        "resizable": True,
                        "minWidth": 100
                    }
                },
                style={"height": "400px"},
                className="ag-theme-quartz compact"
            )
        ])
        
        # Guardar DataFrame procesado para el matching
        oracle_data_store = df.to_dict('records')
        
        return oracle_table, None, oracle_data_store
        
    

# Callback para crear la tabla de matching
@callback(
    [Output('matching-table', 'children'),
     Output('matching-data-store', 'data')],
    [Input('sunat-data-store', 'data'),
     Input('oracle-data-store', 'data')]
)
def create_matching_table(sunat_data, oracle_data):
    if sunat_data is None or oracle_data is None:
        return None, None
    
    # Convertir los datos a DataFrames
    df_sunat = pd.DataFrame(sunat_data)
    df_oracle = pd.DataFrame(oracle_data)
   
    # Hacer el merge por ruc y factura_limpia
    df_merged = pd.merge(
        
        df_oracle,
        df_sunat,
        on=['ruc', 'ruc'],
        how='left',
        suffixes=('_oracle', '_sunat')
    )
    df_merged["GD NUMERO DEPOSITO"]=df_merged["Número de constancia"].fillna("-")
    df_merged["GD FECHA DE PAGO"]=df_merged["Fecha Pago"].fillna("-")
    print(df_merged.columns)
    # Crear la tabla de matching
    matching_table = html.Div([
        dmc.Title(f"Tabla de Matching - Total de coincidencias: {len(df_merged)}", order=4, mb=15, style={'marginTop': '20px'}),
        AgGrid(
            id='matching-data-grid',
            rowData=df_merged.to_dict('records'),
            columnDefs=[
                {
                    "field": col,
                    "filter": True,
                    "sortable": True,
                    "resizable": True,
                    "headerName": col
                } for col in df_merged.columns
            ],
            columnSize="sizeToFit",
            dashGridOptions={
                "animateRows": True,
                "defaultColDef": {
                    "resizable": True,
                    "minWidth": 100
                }
            },
            style={"height": "500px"},
            className="ag-theme-quartz compact"
        )
    ])
    
    # Guardar datos para descarga
    matching_data_store = df_merged.to_dict('records')
    
    return matching_table, matching_data_store


# Callback para descargar el CSV del matching
@callback(
    Output('download-dataframe-xlsx-sunat_oracle_det', 'data'),
    Input('btn-download-sunat_oracle_det', 'n_clicks'),
    State('matching-data-store', 'data'),
    prevent_initial_call=True
)
def download_matching_csv(n_clicks, matching_data):
    if matching_data is None or n_clicks is None:
        return None
    
    # Convertir los datos a DataFrame
    df = pd.DataFrame(matching_data)
    
    if df.empty:
        return None
    
    # Generar nombre de archivo con timestamp
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"matching_sunat_oracle_{timestamp}.csv"
    
    # Descargar como CSV
    return dcc.send_data_frame(df.to_csv, filename, index=False, encoding='utf-8-sig')
