import base64
import io
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback, dash_table
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from constants import PAGE_TITLE_PREFIX
from datetime import datetime

dash.register_page(
    __name__,
    path="/apg/conciliacion-transform",
    title=PAGE_TITLE_PREFIX + "Conciliación BCP",
)

def get_transaction_type(amount, utc):
    try:
        if isinstance(amount, str):
            amt = float(amount.replace(',', ''))
        else:
            amt = float(amount)
    except:
        amt = 0
    
    utc = str(utc).strip()
    fee_utcs = ['0101', '4991', '4923', '0909', '4032', '4997', '4936']
    transfer_utcs = ['4406']
    
    if utc in fee_utcs:
        return 'FEE'
    if utc in transfer_utcs:
        return 'TRANSFER'
    if amt > 0:
        return 'CREDIT'
    return 'DEBIT'

layout = dmc.Container(
    size="lg",
    mt=40,
    children=[
        dmc.Title("Conciliación Transform", order=2, fw=500, mb=10),
        dmc.Text("Sube el archivo CSV para visualizar una vista previa y descargarlo en la plantilla de Oracle.", c="dimmed", mb=30, size="sm"),
        
        dcc.Upload(
            id='upload-data-bcp',
            children=html.Div([
                DashIconify(icon="tabler:cloud-upload", width=30, color="#6c757d", style={"marginBottom": 10}),
                dmc.Text("Arrastra o haz clic para subir CSV", size="sm", fw=500),
            ], style={
                'display': 'flex',
                'flexDirection': 'column',
                'alignItems': 'center',
                'justifyContent': 'center',
                'padding': '30px',
                'border': '1px dashed #495057', # Darker border for dark mode compatibility
                'borderRadius': '6px',
                'cursor': 'pointer',
                'backgroundColor': 'rgba(255, 255, 255, 0.02)'
            }),
            multiple=False
        ),
        
        dmc.Space(h=30),
        html.Div(id='output-preview-bcp'),
        dcc.Store(id='store-processed-data'),
        dcc.Download(id="download-dataframe-csv-bcp"),
    ]
)

@callback(
    [Output('output-preview-bcp', 'children'),
     Output('store-processed-data', 'data')],
    Input('upload-data-bcp', 'contents'),
    State('upload-data-bcp', 'filename'),
    prevent_initial_call=True
)
def process_upload(contents, filename):
    if contents is None:
        return None, None

    try:
        content_type, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)
        data_str = decoded.decode('latin-1')
        df = pd.read_csv(io.StringIO(data_str), skiprows=4,dtype={'Operación - Número':str,"Monto":str})
        df["Monto"] = df["Monto"].str.replace(',','').astype(float)
        df = df.dropna(subset=['Fecha', 'Monto'], how='all')
        if '' in df.columns:
            df = df.drop(columns=[''])

        expected_cols = ['Fecha', 'Descripción operación', 'Monto', 'Operación - Número', 'UTC']
        missing_cols = [c for c in expected_cols if c not in df.columns]
        if missing_cols:
            return dmc.Alert(
                f"Faltan columnas: {', '.join(missing_cols)}",
                color="red",
                icon=DashIconify(icon="tabler:alert-circle"),
            ), None

        df['temp_date'] = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
        if df['temp_date'].isnull().any():
             df.loc[df['temp_date'].isnull(), 'temp_date'] = pd.to_datetime(df['Fecha'], errors='coerce')
        df['oracle_date'] = df['temp_date'].dt.strftime('%m/%d/%Y')
        
        df['oracle_type'] = df.apply(lambda row: get_transaction_type(row['Monto'], row['UTC']), axis=1)
        
        oracle_df = pd.DataFrame()
        oracle_df['Date (MM/DD/YYYY)'] = df['oracle_date']
        oracle_df['Payer/Payee Name'] = ''
        oracle_df['Transaction Id'] = df['Operación - Número'].fillna('').astype(str)
        oracle_df['Transaction Type'] = df['oracle_type']
        oracle_df['Amount'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0)
        oracle_df['Amount'] = oracle_df['Amount'].map('{:.2f}'.format)
        oracle_df['Memo'] = df['Descripción operación'].fillna('')
        oracle_df['NS Internal Customer Id'] = ''
        oracle_df['NS Customer Name'] = ''
        oracle_df['Invoice Number(s)'] = ''
        print(oracle_df.info())
        # Generar vista previa
        preview_table = dash_table.DataTable(
            data=oracle_df.head(10).to_dict('records'),
            columns=[{'name': i, 'id': i} for i in oracle_df.columns],
            style_as_list_view=True,
            style_table={'overflowX': 'auto'},
            style_header={
                'backgroundColor': 'rgba(255, 255, 255, 0.05)',
                'fontWeight': '600',
                'borderBottom': '1px solid rgba(255, 255, 255, 0.1)'
            },
            style_cell={
                'padding': '12px 15px',
                'textAlign': 'left',
                'fontFamily': 'inherit',
                'fontSize': '13px',
                'backgroundColor': 'transparent',
                'borderBottom': '1px solid rgba(255, 255, 255, 0.05)'
            },
        )

        preview_div = html.Div([
            html.Div(
                style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'flex-end', 'marginBottom': '15px'},
                children=[
                    html.Div([
                        dmc.Text("Vista Previa (Primeras 10 filas)", fw=500, size="sm"),
                        dmc.Text(f"Total a exportar: {len(oracle_df)} registros", size="xs", c="dimmed"),
                    ]),
                    dmc.Button(
                        "Descargar CSV",
                        id="btn-download-bcp",
                        leftSection=DashIconify(icon="tabler:download"),
                        color="blue",
                        size="sm",
                        variant="light"
                    )
                ]
            ),
            dmc.Paper(preview_table, withBorder=True, radius="md", p=0, style={"overflow": "hidden"})
        ])

        return preview_div, oracle_df.to_dict('records')

    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return dmc.Alert(
            f"Error: {str(e)}",
            color="red",
            icon=DashIconify(icon="tabler:alert-circle"),
        ), None

@callback(
    Output("download-dataframe-csv-bcp", "data"),
    Input("btn-download-bcp", "n_clicks"),
    State("store-processed-data", "data"),
    prevent_initial_call=True
)
def download_data(n_clicks, data):
    if n_clicks and data:
        df = pd.DataFrame(data)
        print(df["Transaction Id"].unique())
        filename = f"BCP_Oracle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    return dash.no_update
