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
from datetime import datetime, timedelta, time

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
def calcular_horas(hi, hf, jornal):
    formato = "%H:%M"
    hi = datetime.strptime(hi, formato)
    hf = datetime.strptime(hf, formato)

    if hf <= hi:
        hf += timedelta(days=1)

    # Máximo de horas ordinarias
    max_ordinarias = 8.0 if jornal == 6 else 9.6

    # Horas Totales Raw
    duration_raw = (hf - hi).total_seconds() / 3600

    # Determinar deducción de refrigerio
    # Regla: Si las horas trabajadas (duration_raw) son menores a 5 horas -> No reducción (0h)
    # Esto aplica tanto para turno MAÑANA como NOCHE
    
    deduction = 1.0
    if duration_raw < 5:
        deduction = 0.0

    # Horas reales (menos refrigerio/deducción)
    horas_reales = duration_raw - deduction

    # Segementación de Horas
    # Simular boundaries
    day_start = datetime.combine(hi.date(), time(6, 0))
    night_start = datetime.combine(hi.date(), time(22, 0))
    day_2_start = datetime.combine(hi.date() + timedelta(days=1), time(6, 0))
    
    # Ajustar boundaries relativos a hi
    if night_start < hi: night_start += timedelta(days=1)
    if day_2_start < night_start: day_2_start += timedelta(days=1)

    # Calculo de segmentos raw
    raw_day1 = 0.0
    raw_night = 0.0
    raw_day2 = 0.0
    
    current = hi
    while current < hf:
        # Definir el hito siguiente (22:00 o 06:00)
        candidates = [
            datetime.combine(current.date(), time(6, 0)),
            datetime.combine(current.date(), time(22, 0)),
            datetime.combine(current.date() + timedelta(days=1), time(6, 0)),
            datetime.combine(current.date() + timedelta(days=1), time(22, 0))
        ]
        next_mark = min([c for c in candidates if c > current])
        
        step_end = min(hf, next_mark)
        duration = (step_end - current).total_seconds() / 3600
        
        # Clasificar intervalo
        mid = current + (step_end - current)/2
        if 6 <= mid.hour < 22:
            # Day
            if current < night_start and step_end <= night_start:
                 raw_day1 += duration
            else:
                 raw_day2 += duration
        else:
            # Night
            raw_night += duration
            
        current = step_end

    # Determinación de Turno (M vs N) basado en Hora de Inicio
    es_turno_noche = hi.hour >= 13

    if es_turno_noche: 
        # Lógica Turno NOCHE (Night First / Special Allocation)
        
        # Refrigerio (deduction) se resta de Noche
        # Refrigerio (deduction) se resta de Noche, luego de Day2, y finalmente de Day1
        if raw_night >= deduction:
            net_night = raw_night - deduction
            net_day2 = raw_day2
            net_day1 = raw_day1
        else:
             # Si no hay suficiente noche, restar del dia post (Day 2)
             remainder = deduction - raw_night
             net_night = 0
             
             if raw_day2 >= remainder:
                 net_day2 = raw_day2 - remainder
                 net_day1 = raw_day1
             else:
                 # Si tampoco alcanza dia post, restar de dia pre (Day 1)
                 remainder -= raw_day2
                 net_day2 = 0
                 net_day1 = max(0, raw_day1 - remainder) 
        
        # Asignacion Ordinarias
        cap = max_ordinarias
        
        # 1. Day 1 (Pre-Night) - Fill first
        ord_day1 = min(net_day1, cap)
        cap -= ord_day1
        
        # 2. Night (Core) - Fill second
        ord_night_core = min(net_night, cap)
        cap -= ord_night_core
        
        # 3. Day 2 (Post-Night) - Fill third
        ord_night_ext = min(net_day2, cap)
        cap -= ord_night_ext
        
        # Totales Ordinarios
        horas_diurnas = ord_day1
        horas_nocturnas = ord_night_core + ord_night_ext
        
        # Extras
        rem_day1 = net_day1 - ord_day1 
        rem_night = net_night - ord_night_core 
        rem_day2 = net_day2 - ord_night_ext 
        
        horas_extra_diurnas = rem_day1 + rem_day2
        horas_extra_nocturnas = rem_night
        
        # Guardar fisicas para desglose %
        phys_day_ext = horas_extra_diurnas
        phys_night_ext = horas_extra_nocturnas
        total_extras = phys_day_ext + phys_night_ext
        
        # Variables desglose
        he_diurnas_25 = 0.0
        he_diurnas_35 = 0.0
        he_nocturnas_25 = 0.0
        he_nocturnas_35 = 0.0

        if total_extras > 0:
            # Lógica de distribución de extras:
            # 1. Las primeras 2 horas se pagan como Nocturnas (25%) independientemente de si son fisicamente dia o noche.
            # 2. El excedente (>2h) respeta su naturaleza fisica (Dia -> Diurna 35%, Noche -> Nocturna 35%).
            
            quota_25 = 2.0
            
            # Copias de remanentes fisicos
            curr_day1 = rem_day1
            curr_night = rem_night
            curr_day2 = rem_day2
            
            # 1. Pre-Night Day (Si hubiese) -> Consume quota 25% (paga como Nocturna)
            take = min(curr_day1, quota_25)
            he_nocturnas_25 += take
            quota_25 -= take
            curr_day1 -= take
            # Resto a Diurna 35%
            he_diurnas_35 += curr_day1
            
            # 2. Night -> Consume quota 25%
            take = min(curr_night, quota_25)
            he_nocturnas_25 += take
            quota_25 -= take
            curr_night -= take
            # Resto a Nocturna 35%
            he_nocturnas_35 += curr_night
            
            # 3. Post-Night Day -> Consume quota 25% (paga como Nocturna)
            take = min(curr_day2, quota_25)
            he_nocturnas_25 += take
            quota_25 -= take
            curr_day2 -= take
            # Resto a Diurna 35%
            he_diurnas_35 += curr_day2
            
            # Actualizar sumarios
            horas_extra_nocturnas = he_nocturnas_25 + he_nocturnas_35
            horas_extra_diurnas = he_diurnas_25 + he_diurnas_35
            
    else: 
        # Lógica Turno MAÑANA (Day First / Morning Logic)
        
        # Unificar raw day
        total_raw_day = raw_day1 + raw_day2
        
        # Regla Usuario: "si la hora de ingreso esta entre 6:00 y 21:00 y la hora de salida es mayor a 22:00 
        # la hora de cena o almuerzo (-1) deberia ser descontada para el turno noche"
        
        apply_night_deduction = (hi.hour >= 6) and (raw_night > 0)

        if apply_night_deduction:
            # Deduct from Night First
            if raw_night >= deduction:
                net_night = raw_night - deduction
                net_day = total_raw_day
            else:
                 # Si no alcanza la noche, restar del dia
                 remainder = deduction - raw_night
                 net_night = 0
                 net_day = max(0, total_raw_day - remainder)
        else:
            # Refrigerio (deduction) de Dia
            if total_raw_day >= deduction:
                net_day = total_raw_day - deduction
                net_night = raw_night
            else:
                net_day = 0
                remainder = deduction - total_raw_day
                net_night = max(0, raw_night - remainder)
            
        # Asignacion
        cap = max_ordinarias
        
        horas_diurnas = min(net_day, cap)
        cap -= horas_diurnas
        
        horas_nocturnas = min(net_night, cap)
        cap -= horas_nocturnas
        
        # Extras (Fisicas)
        rem_day = net_day - horas_diurnas
        rem_night = net_night - horas_nocturnas
        
        horas_extra_diurnas = rem_day
        horas_extra_nocturnas = rem_night
        
        # Desglose Porcentual Turno Mañana:
        # Cronológico: Mañana -> Noche.
        # Primeras 2h del total -> 25%. Resto -> 35%.
        # Llenamos buckets 25% con DayExt primero, luego NightExt.
        
        phys_day_ext = horas_extra_diurnas
        phys_night_ext = horas_extra_nocturnas
        
        quota_25 = 2.0
        
        # 1. Fill 25% with Day
        use_day_25 = min(phys_day_ext, quota_25)
        he_diurnas_25 = use_day_25
        quota_25 -= use_day_25
        rem_day = phys_day_ext - use_day_25
        
        # 2. Fill 25% with Night (if any quota left)
        use_night_25 = min(phys_night_ext, quota_25)
        he_nocturnas_25 = use_night_25
        # quota_25 -= use_night_25 (Not needed anymore)
        rem_night = phys_night_ext - use_night_25
        
        # 3. Rest goes to 35%
        he_diurnas_35 = rem_day
        he_nocturnas_35 = rem_night

    return {
        "horas_reales": round(horas_reales, 2),
        "horas_diurnas": round(horas_diurnas, 2),
        "horas_nocturnas": round(horas_nocturnas, 2),
        "horas_extra_diurnas": round(horas_extra_diurnas, 2),
        "horas_extra_nocturnas": round(horas_extra_nocturnas, 2),
        "he_diurnas_25": round(he_diurnas_25, 2),
        "he_diurnas_35": round(he_diurnas_35, 2),
        "he_nocturnas_25": round(he_nocturnas_25, 2),
        "he_nocturnas_35": round(he_nocturnas_35, 2),
    }




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
            
            # Drop unnecessary columns safely
            df.drop(["Unnamed: 0", "OBSERVACIONES"], axis=1, errors='ignore', inplace=True)
            
            df.columns = df.columns.str.strip().str.upper()
            
            # Validate required columns
            required_cols = ["HI (BIOMETRICO)", "HF (BIOMETRICO)"]
            missing_cols = [col for col in required_cols if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Faltan columnas requeridas: {missing_cols}. Columnas encontradas: {list(df.columns)}")

            df = df[~df["HI (BIOMETRICO)"].isin(["FALTA", "PERMISO/ FALTA", "DESCANSO", "AUSENTE/ FALTA"])]
            df = df[df["HI (BIOMETRICO)"].notna()]
            
            # Convertir a datetime sin forzar formato estricto para soportar HH:MM y HH:MM:SS
            #df["HI (BIOMETRICO)"] = pd.to_datetime(df["HI (BIOMETRICO)"].astype(str), errors='coerce',format="%H:%M").dt.time
            #df["HF (BIOMETRICO)"] = pd.to_datetime(df["HF (BIOMETRICO)"].astype(str), errors='coerce',format="%H:%M").dt.time
            
            # Wrapper to safely call calcular_horas
            def safe_calc(row):
                # Ensure input is HH:MM string
                def clean(t): 
                    if pd.isna(t) or t == "" or str(t).strip() == "-": return None
                    
                    # Already a time/datetime object
                    if hasattr(t, 'strftime'):
                        return t.strftime("%H:%M")
                    
                    s = str(t).strip()
                    if not s or s == "-": return None

                    try:
                        # Try parsing with pandas (handles "9:00", "09:00:00", "2024-01-01 9:00")
                        # This is much safer than s[:5] which fails on "9:00:00" -> "9:00:"
                        return pd.to_datetime(s).strftime("%H:%M")
                    except:
                        # Fallback for simple strings manual parsing
                        try:
                           parts = s.replace('.', ':').split(':')
                           if len(parts) >= 2:
                               return f"{int(parts[0]):02d}:{int(parts[1]):02d}"
                        except:
                           pass
                    # If all else fails
                    return None
                
                # Validate jornal
                try: 
                    j = float(row["JORNADA A LA SEMANA"]) 
                except: 
                    j = 6
                if j not in [5, 6]: 
                    j = 6
                
                hi_clean = clean(row["HI (BIOMETRICO)"])
                hf_clean = clean(row["HF (BIOMETRICO)"])

                if hi_clean is None or hf_clean is None:
                    return pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0])

                try:
                    res = calcular_horas(hi_clean, hf_clean, j)
                    return pd.Series([
                        res["horas_reales"], 
                        res["horas_diurnas"], 
                        res["horas_nocturnas"], 
                        res["horas_extra_diurnas"], 
                        res["horas_extra_nocturnas"],
                        res["he_diurnas_25"],
                        res["he_diurnas_35"],
                        res["he_nocturnas_25"],
                        res["he_nocturnas_35"]
                    ])
                except Exception as e:
                    # Fallback for bad rows
                    return pd.Series([0, 0, 0, 0, 0, 0, 0, 0, 0])

            df[[
                "HRS DE TRABAJO REALES 2",
                "HORAS DIURNAS",
                "HORAS NOCTURNAS",
                "HORAS EXTRAS DIURNAS",
                "HORAS EXTRAS NOCTURNAS",
                "HE DIURNAS 25%",
                "HE DIURNAS 35%",
                "HE NOCTURNAS 25%",
                "HE NOCTURNAS 35%"
             ]] = df.apply(safe_calc, axis=1)
            
            
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
    print(f"dataframe size: {final_df.shape}")
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
