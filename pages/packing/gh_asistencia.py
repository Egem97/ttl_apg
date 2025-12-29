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
from datetime import datetime, timedelta

# 🚀 Configuraciones de rendimiento optimizadas
pd.options.mode.chained_assignment = None  # Evitar warnings de SettingWithCopyWarning
pd.options.compute.use_numba = True  # Usar Numba para operaciones numéricas si está disponible
pd.options.mode.sim_interactive = True  # Optimizar para operaciones interactivas

dash.register_page(__name__, "/packing/gh_asistencia", title=PAGE_TITLE_PREFIX + "Asistencia")
app = dash.get_app()
PAGE_ID = "gh_asistencia-"
DATA_SOURCE = "gh_asistencia"


def create_custom_layout():
    return dmc.Container(children=[
        Row([
            Column([
                dmc.Title("Asistencia")
            ], size=6),
            Column([
                dcc.Upload(
                    id='upload-data',
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
                html.Div(id='output-data-upload')
            ])
        ]),
        Row([
            Column([
                dmc.Group([
                    dmc.Button("Descargar Excel", id="btn-download"),
                    dcc.Download(id="download-dataframe-xlsx"),
                    dcc.Store(id="gh-asistencia-store"),
                ], mb=10),
                
            ])
        ])
    ], fluid=True)

layout = create_custom_layout()

# ============================================================
# CALLBACKS MANUALES
# ============================================================

def calculate_time_details(row):
    hi = row['HI (BIOMETRICO)']
    hf = row['HF (BIOMETRICO)']
    
    if pd.isna(hi) or pd.isna(hf):
        return pd.Series([0]*9, index=[
            'HRS DE TRABAJO REALES', 'HORAS DIURNAS', 'HORAS NOCTURNAS', 
            'HORAS EXTRAS DIURNAS', 'HORAS EXTRAS NOCTURNAS',
            'HE DIURNAS 25%', 'HE DIURNAS 35%',
            'HE NOCTURNAS 25%', 'HE NOCTURNAS 35%'
        ])
    
    # Create datetime objects
    base_date = datetime(2000, 1, 1)
    
    try:
        start = datetime.combine(base_date, hi)
        end = datetime.combine(base_date, hf)
    except:
        return pd.Series([0]*9, index=[
            'HRS DE TRABAJO REALES', 'HORAS DIURNAS', 'HORAS NOCTURNAS', 
            'HORAS EXTRAS DIURNAS', 'HORAS EXTRAS NOCTURNAS',
            'HE DIURNAS 25%', 'HE DIURNAS 35%',
            'HE NOCTURNAS 25%', 'HE NOCTURNAS 35%'
        ])
    
    if end < start:
        end += timedelta(days=1)
        
    # 1. Bucket Minute Counting (Day vs Night)
    # Day Window: 06:00 to 22:00
    gross_day_minutes = 0
    gross_night_minutes = 0
    
    current = start
    while current < end:
        h = current.hour
        # Night: 22:00 (22) to 06:00 (6)
        # Day: 06:00 (6) to 22:00 (22)
        if h >= 22 or h < 6:
            gross_night_minutes += 1
        else:
            gross_day_minutes += 1
        current += timedelta(minutes=1)
        
    # 2. Lunch Deduction (60 mins)
    # Assumption: Lunch is taken during the day if possible.
    lunch_minutes = 60
    
    net_day_minutes = 0
    net_night_minutes = 0
    
    if gross_day_minutes >= lunch_minutes:
        net_day_minutes = gross_day_minutes - lunch_minutes
        net_night_minutes = gross_night_minutes
    else:
        net_day_minutes = 0
        remainder = lunch_minutes - gross_day_minutes
        net_night_minutes = max(0, gross_night_minutes - remainder)
        
    total_net_minutes = net_day_minutes + net_night_minutes
    total_hours_real = total_net_minutes / 60
    
    # 3. Ordinary vs Extra Allocation
    ORD_CAPACITY_MINS = 480 # 8 hours
    
    # Fill Ordinary Day first
    ord_day_mins = min(net_day_minutes, ORD_CAPACITY_MINS)
    remaining_ord_cap = ORD_CAPACITY_MINS - ord_day_mins
    
    # Fill Ordinary Night next
    ord_night_mins = min(net_night_minutes, remaining_ord_cap)
    
    # Calculate Extras
    extra_day_mins = net_day_minutes - ord_day_mins
    extra_night_mins = net_night_minutes - ord_night_mins
    
    # 4. 25% vs 35% Allocation (Tier 1 = First 120 mins of Extra)
    TIER_1_CAP_MINS = 120 # 2 hours
    
    # Fill Tier 1 with Day Extras first
    he_day_25_mins = min(extra_day_mins, TIER_1_CAP_MINS)
    remaining_tier_1_cap = TIER_1_CAP_MINS - he_day_25_mins
    he_day_35_mins = extra_day_mins - he_day_25_mins
    
    # Fill Tier 1 with Night Extras
    he_night_25_mins = min(extra_night_mins, remaining_tier_1_cap)
    he_night_35_mins = extra_night_mins - he_night_25_mins
    
    return pd.Series([
        round(total_hours_real, 2),
        round(net_day_minutes / 60, 2),
        round(net_night_minutes / 60, 2),
        round(extra_day_mins / 60, 2),
        round(extra_night_mins / 60, 2),
        round(he_day_25_mins / 60, 2),
        round(he_day_35_mins / 60, 2),
        round(he_night_25_mins / 60, 2),
        round(he_night_35_mins / 60, 2)
    ], index=[
        'HRS DE TRABAJO REALES', 'HORAS DIURNAS', 'HORAS NOCTURNAS', 
        'HORAS EXTRAS DIURNAS', 'HORAS EXTRAS NOCTURNAS',
        'HE DIURNAS 25%', 'HE DIURNAS 35%',
        'HE NOCTURNAS 25%', 'HE NOCTURNAS 35%'
    ])

def process_uploaded_file(contents, filename):
    content_type, content_string = contents.split(',')

    decoded = base64.b64decode(content_string)
    try:
        if 'csv' in filename:
            # Assume that the user uploaded a CSV file
            df = pd.read_csv(
                io.StringIO(decoded.decode('utf-8')))
        elif 'xlsx' in filename:
            # Assume that the user uploaded an excel file
            df = pd.read_excel(io.BytesIO(decoded),skiprows=8)
            df.columns = df.columns.str.strip().str.upper()
            df = df[~df["HI (BIOMETRICO)"].isin(["FALTA", "PERMISO/ FALTA", "DESCANSO", "AUSENTE/ FALTA"])]
            df = df[df["HI (BIOMETRICO)"].notna()]
            # Convertir a datetime sin forzar formato estricto para soportar HH:MM y HH:MM:SS
            df["HI (BIOMETRICO)"] = pd.to_datetime(df["HI (BIOMETRICO)"].astype(str), errors='coerce').dt.time
            df["HF (BIOMETRICO)"] = pd.to_datetime(df["HF (BIOMETRICO)"].astype(str), errors='coerce').dt.time
            
            hours_data = df.apply(calculate_time_details, axis=1)
            df = pd.concat([df, hours_data], axis=1)
            # convert time column to string for json serialization
            df["HI (BIOMETRICO)"] = df["HI (BIOMETRICO)"].astype(str)
            df["HF (BIOMETRICO)"] = df["HF (BIOMETRICO)"].astype(str)
            return df
        else:
             return None
            
    except Exception as e:
        print(e)
        return None
    return df

@callback(
    Output('output-data-upload', 'children'),
    Output('gh-asistencia-store', 'data'),
    Input('upload-data', 'contents'),
    State('upload-data', 'filename'),
)
def update_output(list_of_contents, list_of_names):
    if list_of_contents is None:
        return html.Div(), []
    
    dfs = []
    for c, n in zip(list_of_contents, list_of_names):
        df = process_uploaded_file(c, n)
        if df is not None:
            dfs.append(df)
            
    if not dfs:
        return html.Div("Error procesando archivos"), []
        
    final_df = pd.concat(dfs, ignore_index=True)
    
    grid = AgGrid(
            id=f"grid-final",
            rowData=final_df.to_dict('records'),
            columnDefs=[{"field": i} for i in final_df.columns],
            columnSize="sizeToFit",
            dashGridOptions={
                "rowSelection": {'mode': 'multiRow'},
                "animateRows": True,
                "defaultColDef": {
                    "resizable": True,
                    "minWidth": 120,
                    "sortable": True,
                    "filter": True
                }
            },
            style={"height": "400px"},
            className="ag-theme-alpine-dark compact",
        )
    return grid, final_df.to_dict('records')

@callback(
    Output("download-dataframe-xlsx", "data"),
    Input("btn-download", "n_clicks"),
    State("gh-asistencia-store", "data"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, data):
    if not data:
        return None
    
    df = pd.DataFrame(data)
    
    # Generate Excel in memory
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df.to_excel(writer, sheet_name='Sheet1', index=False)
    
    workbook = writer.book
    worksheet = writer.sheets['Sheet1']
    
    # Add Table Style
    (max_row, max_col) = df.shape
    column_settings = [{'header': column} for column in df.columns]
    
    worksheet.add_table(0, 0, max_row, max_col - 1, {
        'columns': column_settings,
        'style': 'TableStyleLight9'
    })
    
    # Auto-adjust columns width (approximate)
    for i, col in enumerate(df.columns):
        # find max len of column values
        max_len = max(
            df[col].astype(str).map(len).max(),
            len(str(col))
        ) + 2
        worksheet.set_column(i, i, max_len)
        
    writer.close()
    data = output.getvalue()
    
    return dcc.send_bytes(data, filename="asistencia_procesada.xlsx")
