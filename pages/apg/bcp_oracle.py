import base64
import csv
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
    title=PAGE_TITLE_PREFIX + "Conciliación Bancaria",
)

ORACLE_COLUMNS = [
    'Date (MM/DD/YYYY)',
    'Payer/Payee Name',
    'Transaction Id',
    'Transaction Type',
    'Amount',
    'Memo',
    'NS Internal Customer Id',
    'NS Customer Name',
    'Invoice Number(s)',
]

BANK_OPTIONS = [
    {"value": "BCP", "label": "BCP"},
    {"value": "SCOTIABANK", "label": "Scotiabank"},
    {"value": "BBVA", "label": "BBVA"},
    {"value": "INTERBANK", "label": "Interbank"},
    {"value": "NACION", "label": "Banco de la Nación"},
]

BANK_ACCEPT = {
    "BCP": ".csv,.xls,.xlsx",
    "SCOTIABANK": ".csv,.xls,.xlsx",
    "BBVA": ".csv,.xls,.xlsx",
    "INTERBANK": ".csv,.xls,.xlsx",
    "NACION": ".csv,.xls,.xlsx",
}


def _empty_oracle_df():
    return pd.DataFrame(columns=ORACLE_COLUMNS)


def _finalize(oracle_df):
    oracle_df = oracle_df.copy()
    oracle_df['Amount'] = pd.to_numeric(oracle_df['Amount'], errors='coerce').fillna(0)
    oracle_df['Amount'] = oracle_df['Amount'].map('{:.2f}'.format)
    for c in ['Payer/Payee Name', 'NS Internal Customer Id', 'NS Customer Name', 'Invoice Number(s)']:
        oracle_df[c] = ''
    oracle_df['Transaction Id'] = oracle_df['Transaction Id'].fillna('').astype(str)
    oracle_df['Memo'] = oracle_df['Memo'].fillna('').astype(str)
    return oracle_df[ORACLE_COLUMNS]


def _is_excel_bytes(decoded):
    # xlsx (zip): 'PK\x03\x04'  |  xls (OLE): '\xD0\xCF\x11\xE0'
    return decoded[:4] in (b'PK\x03\x04', b'\xD0\xCF\x11\xE0')


def _is_html_bytes(decoded):
    head = decoded[:512].lstrip().lower()
    return head.startswith(b'<') or b'<html' in head or b'<table' in head


def _read_bytes_as_excel(decoded):
    """Lee bytes como tabla cruda (sin header) desde xls/xlsx, csv o html."""
    # Excel binario (xls/xlsx)
    if _is_excel_bytes(decoded):
        try:
            return pd.read_excel(io.BytesIO(decoded), sheet_name=None, header=None)
        except Exception:
            pass
    # HTML disfrazado de xls
    if _is_html_bytes(decoded):
        tables = pd.read_html(io.BytesIO(decoded))
        return {f"sheet{i}": t for i, t in enumerate(tables)}
    # CSV (texto plano) — usa csv.reader para tolerar cabeceras con columnas variables
    for enc in ('utf-8-sig', 'latin-1', 'cp1252'):
        try:
            text = decoded.decode(enc)
        except Exception:
            continue
        for sep in (',', ';', '\t', '|'):
            try:
                rows = list(csv.reader(io.StringIO(text), delimiter=sep))
            except Exception:
                continue
            if not rows:
                continue
            max_cols = max((len(r) for r in rows), default=0)
            if max_cols < 2:
                continue
            padded = [r + [None] * (max_cols - len(r)) for r in rows]
            df = pd.DataFrame(padded)
            return {'csv': df}
    # Último intento: HTML
    tables = pd.read_html(io.BytesIO(decoded))
    return {f"sheet{i}": t for i, t in enumerate(tables)}


# -------------------- BCP --------------------
def _bcp_type(amount, utc):
    try:
        amt = float(str(amount).replace(',', ''))
    except Exception:
        amt = 0
    utc = str(utc).strip()
    if utc in ['0101', '4991', '4923', '0909', '4032', '4997', '4936']:
        return 'FEE'
    if utc in ['4406']:
        return 'TRANSFER'
    return 'CREDIT' if amt > 0 else 'DEBIT'


def _bcp_from_excel(decoded):
    sheets = _read_bytes_as_excel(decoded)
    raw = next(iter(sheets.values()))
    expected = ['Fecha', 'Descripción operación', 'Monto', 'Operación - Número', 'UTC']
    header_idx = None
    for i, row in raw.iterrows():
        vals = [str(x).strip() for x in row.values]
        if all(c in vals for c in expected):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No se encontró la fila de cabecera en el archivo BCP")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_idx].values]
    df = df.loc[:, df.columns.notna() & (df.columns != 'nan')]
    df = df.dropna(subset=['Fecha', 'Monto'], how='all')
    return df


def _bcp_from_csv(decoded):
    data_str = decoded.decode('latin-1')
    df = pd.read_csv(io.StringIO(data_str), skiprows=4, dtype={'Operación - Número': str, "Monto": str})
    df["Monto"] = df["Monto"].str.replace(',', '').astype(float)
    df = df.dropna(subset=['Fecha', 'Monto'], how='all')
    if '' in df.columns:
        df = df.drop(columns=[''])
    return df


def process_bcp(decoded):
    df = _bcp_from_excel(decoded) if _is_excel_bytes(decoded) else _bcp_from_csv(decoded)

    expected = ['Fecha', 'Descripción operación', 'Monto', 'Operación - Número', 'UTC']
    missing = [c for c in expected if c not in df.columns]
    if missing:
        raise ValueError(f"Faltan columnas: {', '.join(missing)}")

    temp = pd.to_datetime(df['Fecha'], format='%d/%m/%Y', errors='coerce')
    mask = temp.isnull()
    if mask.any():
        temp.loc[mask] = pd.to_datetime(df.loc[mask, 'Fecha'], errors='coerce')

    out = _empty_oracle_df()
    out['Date (MM/DD/YYYY)'] = temp.dt.strftime('%m/%d/%Y').values
    out['Transaction Id'] = df['Operación - Número'].fillna('').astype(str).values
    out['Transaction Type'] = df.apply(lambda r: _bcp_type(r['Monto'], r['UTC']), axis=1).values
    out['Amount'] = pd.to_numeric(df['Monto'], errors='coerce').fillna(0).values
    out['Memo'] = df['Descripción operación'].fillna('').values
    return _finalize(out)


# -------------------- Scotiabank --------------------
def process_scotiabank(decoded):
    sheets = _read_bytes_as_excel(decoded)
    raw = next(iter(sheets.values()))
    # Find header row containing 'Código' and 'Movimiento'
    header_idx = None
    for i, row in raw.iterrows():
        vals = [str(x).strip() for x in row.values]
        if 'Código' in vals and 'Movimiento' in vals and 'Debe' in vals:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No se encontró la fila de cabecera en el archivo Scotiabank")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = raw.iloc[header_idx].values
    df = df.loc[:, df.columns.notna()]
    df = df.rename(columns=lambda c: str(c).strip())
    # Drop totals / empty rows
    df = df[df['Día'].notna()]
    df = df[df['Código'].astype(str).str.strip().str.lower() != 'total:']
    df = df[df['Código'].notna()]

    def to_num(x):
        try:
            return float(str(x).replace(',', '').replace('$', '').strip() or 0)
        except Exception:
            return 0.0

    debe = df['Debe'].map(to_num)
    haber = df['Haber'].map(to_num)
    codigo = df['Código'].astype(str).str.strip()

    def row_type(cod, d, h):
        if cod == '39':
            return 'TRANSFER'
        if h > 0:
            return 'CREDIT'
        return 'DEBIT'

    amount = haber - debe  # Debe -> negative, Haber -> positive

    fechas = pd.to_datetime(df['Día'], format='%d/%m/%Y', errors='coerce')
    mask = fechas.isnull()
    if mask.any():
        fechas.loc[mask] = pd.to_datetime(df.loc[mask, 'Día'], errors='coerce')

    out = _empty_oracle_df()
    out['Date (MM/DD/YYYY)'] = fechas.dt.strftime('%m/%d/%Y').values
    out['Transaction Id'] = df['Documento'].fillna('').astype(str).values
    out['Transaction Type'] = [row_type(c, d, h) for c, d, h in zip(codigo, debe, haber)]
    out['Amount'] = amount.values
    out['Memo'] = df['Movimiento'].fillna('').astype(str).values
    return _finalize(out)


# -------------------- BBVA --------------------
def process_bbva(decoded):
    sheets = _read_bytes_as_excel(decoded)
    raw = next(iter(sheets.values()))
    header_idx = None
    for i, row in raw.iterrows():
        vals = [str(x).strip() for x in row.values]
        if 'F. Operación' in vals and 'Importe' in vals and 'Concepto' in vals:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No se encontró la fila de cabecera en el archivo BBVA")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_idx].values]
    df = df[df['Código'].notna()]  # quita filas de saldo

    codigo = df['Código'].astype(str).str.strip().str.replace(r'\.0$', '', regex=True)
    importe = pd.to_numeric(df['Importe'], errors='coerce').fillna(0)

    def row_type(cod, imp):
        if cod == '527':
            return 'FEE'
        if cod == '690':
            return 'TRANSFER'
        return 'CREDIT' if imp > 0 else 'DEBIT'

    fechas = pd.to_datetime(df['F. Operación'], errors='coerce')

    out = _empty_oracle_df()
    out['Date (MM/DD/YYYY)'] = fechas.dt.strftime('%m/%d/%Y').values
    out['Transaction Id'] = df['Nº. Doc.'].fillna('').astype(str).values
    out['Transaction Type'] = [row_type(c, i) for c, i in zip(codigo, importe)]
    out['Amount'] = importe.values
    out['Memo'] = df['Concepto'].fillna('').astype(str).values
    return _finalize(out)


# -------------------- Interbank --------------------
def process_interbank(decoded):
    sheets = _read_bytes_as_excel(decoded)
    raw = next(iter(sheets.values()))
    header_idx = None
    for i, row in raw.iterrows():
        vals = [str(x).strip() for x in row.values]
        if 'Fecha de operación' in vals and 'Movimiento' in vals and 'Cargo' in vals:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No se encontró la fila de cabecera en el archivo Interbank")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_idx].values]
    df = df.loc[:, df.columns.notna() & (df.columns != 'nan')]
    df = df[df['Fecha de operación'].notna()]

    def to_num(x):
        if pd.isna(x):
            return 0.0
        try:
            return float(str(x).replace(',', '').strip() or 0)
        except Exception:
            return 0.0

    cargo = df['Cargo'].map(to_num)
    abono = df['Abono'].map(to_num)
    # Cargo viene negativo, Abono positivo. Amount = cargo + abono (respeta signo del cargo)
    amount = cargo + abono

    tipo = ['CREDIT' if a > 0 else 'DEBIT' for a in amount]

    fechas = pd.to_datetime(df['Fecha de operación'], format='%d/%m/%Y', errors='coerce')
    mask = fechas.isnull()
    if mask.any():
        fechas.loc[mask] = pd.to_datetime(df.loc[mask, 'Fecha de operación'], errors='coerce')

    nro = df['Nro. de operación'].astype(str).str.strip()
    fallback_id = fechas.dt.strftime('%d%m%Y')
    tx_id = [fb if (n in ('-', '', 'nan', 'None')) else n for n, fb in zip(nro, fallback_id)]

    out = _empty_oracle_df()
    out['Date (MM/DD/YYYY)'] = fechas.dt.strftime('%m/%d/%Y').values
    out['Transaction Id'] = tx_id
    out['Transaction Type'] = tipo
    out['Amount'] = amount.values
    out['Memo'] = df['Movimiento'].fillna('').astype(str).values
    return _finalize(out)


# -------------------- Banco de la Nación --------------------
def process_nacion(decoded):
    sheets = _read_bytes_as_excel(decoded)
    raw = next(iter(sheets.values()))
    header_idx = None
    for i, row in raw.iterrows():
        vals = [str(x).strip() for x in row.values]
        if 'Fecha' in vals and 'Trans.' in vals and 'Documento' in vals:
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("No se encontró la fila de cabecera en el archivo Banco de la Nación")

    df = raw.iloc[header_idx + 1:].copy()
    df.columns = [str(c).strip() for c in raw.iloc[header_idx].values]
    df = df[df['Fecha'].notna()]

    def to_num(x):
        if pd.isna(x):
            return 0.0
        try:
            return float(str(x).replace(',', '').strip() or 0)
        except Exception:
            return 0.0

    cargo = df['Cargo'].map(to_num)
    abono = df['Abono'].map(to_num)
    # Cargo viene ya con signo negativo en el archivo del BN (ej. -52,810.00).
    # Amount = cargo + abono (respeta el signo negativo del cargo).
    amount = cargo + abono
    # Tipo según la columna donde está el movimiento: Cargo -> DEBIT, Abono -> CREDIT.
    tipo = ['DEBIT' if c != 0 else 'CREDIT' for c, _ in zip(cargo, abono)]

    fechas = pd.to_datetime(df['Fecha'], format='%Y.%m.%d', errors='coerce')
    mask = fechas.isnull()
    if mask.any():
        fechas.loc[mask] = pd.to_datetime(df.loc[mask, 'Fecha'], errors='coerce')

    out = _empty_oracle_df()
    out['Date (MM/DD/YYYY)'] = fechas.dt.strftime('%m/%d/%Y').values
    out['Transaction Id'] = df['Documento'].fillna('').astype(str).values
    out['Transaction Type'] = tipo
    out['Amount'] = amount.values
    out['Memo'] = df['Trans.'].fillna('').astype(str).values
    return _finalize(out)


PROCESSORS = {
    "BCP": process_bcp,
    "SCOTIABANK": process_scotiabank,
    "BBVA": process_bbva,
    "INTERBANK": process_interbank,
    "NACION": process_nacion,
}


layout = dmc.Container(
    fluid=True,
    mt=30,
    px=30,
    children=[
        dmc.Title("Conciliación Bancaria", order=2, fw=500, mb=4),
        dmc.Text(
            "Selecciona el banco, sube el archivo en su formato original y descarga el CSV listo para Oracle.",
            c="dimmed", mb=20, size="sm"
        ),

        dmc.Grid(
            gutter="md",
            mb=20,
            children=[
                dmc.GridCol(
                    span={"base": 12, "md": 3},
                    children=dmc.Select(
                        id='bank-select',
                        label="Banco",
                        placeholder="Selecciona un banco",
                        data=BANK_OPTIONS,
                        value="BCP",
                    ),
                ),
                dmc.GridCol(
                    span={"base": 12, "md": 9},
                    children=html.Div(id='upload-container'),
                ),
            ],
        ),

        html.Div(id='output-preview-bcp'),
        dcc.Store(id='store-processed-data'),
        dcc.Download(id="download-dataframe-csv-bcp"),
    ]
)


@callback(
    Output('upload-container', 'children'),
    Input('bank-select', 'value'),
)
def render_upload(bank):
    accept = BANK_ACCEPT.get(bank or 'BCP', '.csv,.xls,.xlsx')
    label = "CSV o Excel (.xls / .xlsx)"
    return dcc.Upload(
        id='upload-data-bcp',
        accept=accept,
        style={"marginTop": "24px"},
        children=html.Div([
            DashIconify(icon="tabler:cloud-upload", width=22, color="#6c757d", style={"marginRight": 10}),
            dmc.Text(f"Arrastra o haz clic para subir {label}", size="sm", fw=500),
        ], style={
            'display': 'flex',
            'flexDirection': 'row',
            'alignItems': 'center',
            'justifyContent': 'center',
            'padding': '12px 20px',
            'border': '1px dashed #495057',
            'borderRadius': '6px',
            'cursor': 'pointer',
            'backgroundColor': 'rgba(255, 255, 255, 0.02)',
            'minHeight': '42px',
        }),
        multiple=False
    )


@callback(
    [Output('output-preview-bcp', 'children'),
     Output('store-processed-data', 'data')],
    Input('upload-data-bcp', 'contents'),
    State('upload-data-bcp', 'filename'),
    State('bank-select', 'value'),
    prevent_initial_call=True
)
def process_upload(contents, filename, bank):
    if contents is None:
        return None, None

    try:
        _, content_string = contents.split(',')
        decoded = base64.b64decode(content_string)

        processor = PROCESSORS.get(bank)
        if processor is None:
            return dmc.Alert("Banco no soportado", color="red",
                             icon=DashIconify(icon="tabler:alert-circle")), None

        oracle_df = processor(decoded)

        COL_LABELS = {
            'Date (MM/DD/YYYY)': 'Fecha',
            'Payer/Payee Name': 'Payer / Payee',
            'Transaction Id': 'Transaction ID',
            'Transaction Type': 'Tipo',
            'Amount': 'Monto',
            'Memo': 'Memo',
            'NS Internal Customer Id': 'NS Customer ID',
            'NS Customer Name': 'NS Customer',
            'Invoice Number(s)': 'Invoice #',
        }
        MONO = "ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"

        preview_table = dash_table.DataTable(
            data=oracle_df.head(15).to_dict('records'),
            columns=[{'name': COL_LABELS.get(c, c), 'id': c} for c in oracle_df.columns],
            page_size=15,
            cell_selectable=False,
            style_table={'overflowX': 'auto', 'width': '100%', 'borderCollapse': 'separate'},
            style_header={
                'backgroundColor': 'rgba(255, 255, 255, 0.04)',
                'color': 'rgba(255, 255, 255, 0.65)',
                'fontWeight': '600',
                'fontSize': '11px',
                'textTransform': 'uppercase',
                'letterSpacing': '0.6px',
                'padding': '14px 14px',
                'border': 'none',
                'borderBottom': '1px solid rgba(255, 255, 255, 0.12)',
                'whiteSpace': 'nowrap',
                'height': 'auto',
            },
            style_cell={
                'padding': '12px 14px',
                'textAlign': 'left',
                'fontFamily': 'inherit',
                'fontSize': '13px',
                'color': 'rgba(255, 255, 255, 0.88)',
                'backgroundColor': 'transparent',
                'border': 'none',
                'borderBottom': '1px solid rgba(255, 255, 255, 0.04)',
                'whiteSpace': 'nowrap',
                'overflow': 'hidden',
                'textOverflow': 'ellipsis',
                'maxWidth': '280px',
            },
            style_cell_conditional=[
                {'if': {'column_id': 'Date (MM/DD/YYYY)'}, 'width': '110px', 'fontFamily': MONO, 'color': 'rgba(255,255,255,0.7)'},
                {'if': {'column_id': 'Payer/Payee Name'}, 'width': '130px'},
                {'if': {'column_id': 'Transaction Id'}, 'width': '140px', 'fontFamily': MONO},
                {'if': {'column_id': 'Transaction Type'}, 'width': '120px'},
                {'if': {'column_id': 'Amount'}, 'width': '130px', 'textAlign': 'right', 'fontFamily': MONO, 'fontWeight': '600'},
                {'if': {'column_id': 'Memo'}, 'minWidth': '240px'},
                {'if': {'column_id': 'NS Internal Customer Id'}, 'width': '150px'},
                {'if': {'column_id': 'NS Customer Name'}, 'width': '140px'},
                {'if': {'column_id': 'Invoice Number(s)'}, 'width': '120px'},
            ],
            style_data_conditional=[
                # Zebra striping
                {'if': {'row_index': 'odd'}, 'backgroundColor': 'rgba(255,255,255,0.015)'},
                # Hover
                {'if': {'state': 'active'}, 'backgroundColor': 'rgba(59,130,246,0.08)', 'border': 'none'},
                # Type badges
                {
                    'if': {'filter_query': '{Transaction Type} = "CREDIT"', 'column_id': 'Transaction Type'},
                    'color': '#4ade80', 'fontWeight': '600', 'fontSize': '11px', 'letterSpacing': '0.5px',
                },
                {
                    'if': {'filter_query': '{Transaction Type} = "DEBIT"', 'column_id': 'Transaction Type'},
                    'color': '#f87171', 'fontWeight': '600', 'fontSize': '11px', 'letterSpacing': '0.5px',
                },
                {
                    'if': {'filter_query': '{Transaction Type} = "TRANSFER"', 'column_id': 'Transaction Type'},
                    'color': '#60a5fa', 'fontWeight': '600', 'fontSize': '11px', 'letterSpacing': '0.5px',
                },
                {
                    'if': {'filter_query': '{Transaction Type} = "FEE"', 'column_id': 'Transaction Type'},
                    'color': '#fbbf24', 'fontWeight': '600', 'fontSize': '11px', 'letterSpacing': '0.5px',
                },
                # Amount color by sign
                {
                    'if': {'filter_query': '{Transaction Type} = "CREDIT"', 'column_id': 'Amount'},
                    'color': '#4ade80',
                },
                {
                    'if': {'filter_query': '{Transaction Type} = "DEBIT"', 'column_id': 'Amount'},
                    'color': '#f87171',
                },
                # Dim empty NS columns
                {'if': {'column_id': 'Payer/Payee Name'}, 'color': 'rgba(255,255,255,0.35)'},
                {'if': {'column_id': 'NS Internal Customer Id'}, 'color': 'rgba(255,255,255,0.35)'},
                {'if': {'column_id': 'NS Customer Name'}, 'color': 'rgba(255,255,255,0.35)'},
                {'if': {'column_id': 'Invoice Number(s)'}, 'color': 'rgba(255,255,255,0.35)'},
            ],
        )

        bank_label = next((b['label'] for b in BANK_OPTIONS if b['value'] == bank), bank)

        header_row = html.Div(
            style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'marginBottom': '14px'},
            children=[
                dmc.Group(gap=8, children=[
                    dmc.Badge(bank_label, color="blue", variant="light", radius="sm"),
                    dmc.Text("Vista previa", fw=600, size="sm"),
                    dmc.Text(f"· primeras {min(15, len(oracle_df))} de {len(oracle_df)} filas", size="xs", c="dimmed"),
                ]),
                dmc.Button(
                    "Descargar CSV",
                    id="btn-download-bcp",
                    leftSection=DashIconify(icon="tabler:download"),
                    color="blue",
                    size="sm",
                    variant="filled",
                ),
            ]
        )

        preview_div = html.Div([
            header_row,
            dmc.Paper(
                preview_table,
                withBorder=True, radius="md", p=0,
                style={"overflow": "hidden", "backgroundColor": "rgba(255,255,255,0.01)"}
            ),
        ])

        stored = {'bank': bank, 'records': oracle_df.to_dict('records')}
        return preview_div, stored

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
        bank = data.get('bank', 'BCP') if isinstance(data, dict) else 'BCP'
        records = data.get('records', []) if isinstance(data, dict) else data
        df = pd.DataFrame(records)
        filename = f"{bank}_Oracle_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return dcc.send_data_frame(df.to_csv, filename, index=False)
    return dash.no_update
