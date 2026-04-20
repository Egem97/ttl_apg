import io
import base64
import time
import dash
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_ag_grid import AgGrid

from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
from helpers.files import load_data_agritracer


pd.options.mode.chained_assignment = None


dash.register_page(__name__, "/apg/transporte-agri", title=PAGE_TITLE_PREFIX + "Transportes match")
app = dash.get_app()
PAGE_ID = "transporte-agri-"


AGRI_COLUMNS = ["DOCUMENTO", "EMPRESA", "FECHA", "TRABAJADOR"]
EXCEL_DNI_COL = "DNI"
EXCEL_FECHA_COL = "Fecha Registro"


def _normalize_dni(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.replace(r"\D", "", regex=True)
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return s


def _normalize_fecha(series: pd.Series) -> pd.Series:
    if pd.api.types.is_datetime64_any_dtype(series):
        return pd.to_datetime(series, errors="coerce").dt.date

    s = series.astype(str).str.strip()
    s = s.str.replace("-", "/", regex=False)
    s = s.str.split(" ").str[0]

    dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    if dt.isna().any():
        mask = dt.isna() & s.notna() & (s != "nan")
        if mask.any():
            dt.loc[mask] = pd.to_datetime(s[mask], errors="coerce", dayfirst=True)
    return dt.dt.date


def create_custom_layout():
    return dmc.Container(
        children=[
            html.Div(
                [
                    dcc.Store(id=f"{PAGE_ID}agritracer-store"),
                    dcc.Store(id=f"{PAGE_ID}merged-store"),
                    dcc.Store(id=f"{PAGE_ID}loading-trigger", data="init"),
                ]
            ),
            dmc.Container(
                [
                    Row(
                        [
                            Column(
                                [
                                    DashIconify(icon="flat-ui:resume", width=30),
                                    dmc.Title("Transportes match", order=1, mb="xs"),
                                    dmc.Text(
                                        "Carga el Excel de transportes para cruzar con Agritracer por DNI y Fecha.",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                                size=12,
                            )
                        ]
                    ),
                    Row(
                        [
                            Column(
                                [
                                    dcc.Upload(
                                        id=f"{PAGE_ID}upload-excel",
                                        children=html.Div(
                                            [
                                                DashIconify(icon="mdi:file-excel", width=24),
                                                html.Span(
                                                    " Arrastra o selecciona el archivo Excel",
                                                    style={"marginLeft": "8px"},
                                                ),
                                            ]
                                        ),
                                        style={
                                            "height": "60px",
                                            "lineHeight": "60px",
                                            "borderWidth": "1px",
                                            "borderStyle": "dashed",
                                            "borderRadius": "5px",
                                            "textAlign": "center",
                                            "margin": "10px 0",
                                        },
                                        multiple=False,
                                        accept=".xlsx,.xls",
                                    ),
                                    dcc.Loading(
                                        id=f"{PAGE_ID}upload-loading",
                                        type="dot",
                                        color="#228be6",
                                        children=html.Div(id=f"{PAGE_ID}upload-status"),
                                    ),
                                ],
                                size=12,
                            )
                        ]
                    ),
                    Row(
                        [
                            Column(
                                [
                                    dcc.Loading(
                                        id=f"{PAGE_ID}loading-indicator",
                                        type="circle",
                                        color="#228be6",
                                        children=html.Div(
                                            id=f"{PAGE_ID}main-table",
                                            style={"minHeight": "200px"},
                                        ),
                                    ),
                                    dmc.Group(
                                        [
                                            dmc.Button(
                                                "DESCARGAR EXCEL",
                                                id=f"{PAGE_ID}btn-xlsx",
                                                color="green",
                                                variant="filled",
                                                leftSection=DashIconify(icon="mdi:file-excel"),
                                                disabled=True,
                                            ),
                                        ],
                                        mt="md",
                                    ),
                                    dcc.Download(id=f"{PAGE_ID}download-xlsx"),
                                ],
                                size=12,
                            )
                        ]
                    ),
                ],
                fluid=True,
            ),
        ],
        fluid=True,
    )


layout = create_custom_layout()


@callback(
    Output(f"{PAGE_ID}agritracer-store", "data"),
    Input(f"{PAGE_ID}loading-trigger", "data"),
)
def load_data_to_store(_):
    df = load_data_agritracer()
    if df is None or df.empty:
        return []
    df = df[[c for c in AGRI_COLUMNS if c in df.columns]].copy()
    return df.to_dict("records")


@callback(
    Output(f"{PAGE_ID}main-table", "children"),
    Output(f"{PAGE_ID}merged-store", "data"),
    Output(f"{PAGE_ID}upload-status", "children"),
    Output(f"{PAGE_ID}btn-xlsx", "disabled"),
    Input(f"{PAGE_ID}upload-excel", "contents"),
    Input(f"{PAGE_ID}agritracer-store", "data"),
    State(f"{PAGE_ID}upload-excel", "filename"),
    prevent_initial_call=True,
)
def process_excel_and_merge(contents, agri_data, filename):
    if not contents:
        return no_update, no_update, no_update, True

    if not agri_data:
        return (
            None,
            None,
            dmc.Alert(
                "Datos de Agritracer no disponibles. Recarga la página.",
                color="red",
                title="Error",
            ),
            True,
        )

    try:
        _, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
        df_excel = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        return (
            None,
            None,
            dmc.Alert(f"Error leyendo el archivo: {e}", color="red", title="Error"),
            True,
        )

    missing = [c for c in (EXCEL_DNI_COL, EXCEL_FECHA_COL) if c not in df_excel.columns]
    if missing:
        return (
            None,
            None,
            dmc.Alert(
                f"Faltan columnas en el Excel: {', '.join(missing)}",
                color="red",
                title="Estructura inválida",
            ),
            True,
        )

    df_agri = pd.DataFrame(agri_data)
    for col in AGRI_COLUMNS:
        if col not in df_agri.columns:
            df_agri[col] = pd.NA

    df_excel["_dni_key"] = _normalize_dni(df_excel[EXCEL_DNI_COL])
    df_excel["_fecha_key"] = _normalize_fecha(df_excel[EXCEL_FECHA_COL])

    df_agri["_dni_key"] = _normalize_dni(df_agri["DOCUMENTO"])
    df_agri["_fecha_key"] = _normalize_fecha(df_agri["FECHA"])
    df_agri_match = (
        df_agri[["_dni_key", "_fecha_key", "EMPRESA", "TRABAJADOR"]]
        .drop_duplicates(subset=["_dni_key", "_fecha_key"], keep="first")
        .rename(columns={"EMPRESA": "AGRI_EMPRESA", "TRABAJADOR": "AGRI_TRABAJADOR"})
    )

    df_merged = df_excel.merge(df_agri_match, on=["_dni_key", "_fecha_key"], how="left")
    df_merged["MATCH_AGRITRACER"] = df_merged["AGRI_EMPRESA"].notna().map({True: "SI", False: "NO"})
    df_merged = df_merged.drop(columns=["_dni_key", "_fecha_key"])

    for col in df_merged.columns:
        if pd.api.types.is_datetime64_any_dtype(df_merged[col]):
            df_merged[col] = df_merged[col].dt.strftime("%d/%m/%Y")

    total = len(df_merged)
    matched = int((df_merged["MATCH_AGRITRACER"] == "SI").sum())

    status = dmc.Alert(
        f"Archivo: {filename} | Filas: {total} | Coincidencias: {matched} | Sin match: {total - matched}",
        color="green" if matched else "yellow",
        title="Cruce completado",
    )

    column_defs = [
        {
            "field": col,
            "filter": True,
            "sortable": True,
            "resizable": True,
            "headerName": col,
        }
        for col in df_merged.columns
    ]

    table = AgGrid(
        id=f"{PAGE_ID}merged-grid",
        rowData=df_merged.to_dict("records"),
        columnDefs=column_defs,
        columnSize="autoSize",
        dashGridOptions={
            "animateRows": True,
            "pagination": True,
            "paginationPageSize": 50,
            "defaultColDef": {"resizable": True, "minWidth": 120, "floatingFilter": False},
        },
        style={"height": "520px"},
        className="ag-theme-quartz compact",
    )

    return table, df_merged.to_dict("records"), status, False


@callback(
    Output(f"{PAGE_ID}download-xlsx", "data"),
    Input(f"{PAGE_ID}btn-xlsx", "n_clicks"),
    State(f"{PAGE_ID}merged-store", "data"),
    State(f"{PAGE_ID}upload-excel", "filename"),
    prevent_initial_call=True,
)
def download_merged_excel(n_clicks, merged_data, original_filename):
    if not n_clicks or not merged_data:
        return no_update

    df = pd.DataFrame(merged_data)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Transportes")
        worksheet = writer.sheets["Transportes"]
        for i, col in enumerate(df.columns):
            max_len = max(df[col].astype(str).map(len).max() if len(df) else 0, len(str(col))) + 2
            worksheet.set_column(i, i, min(max_len, 40))

    base = (original_filename or "transportes").rsplit(".", 1)[0]
    filename = f"{base}_agritracer_{int(time.time())}.xlsx"
    return dcc.send_bytes(output.getvalue(), filename=filename)
