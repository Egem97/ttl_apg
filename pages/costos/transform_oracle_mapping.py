import io
import os
import base64
from datetime import datetime

import dash
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_ag_grid import AgGrid

from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
from helpers.transform.oracle_mapping import transform_oracle_mapping, DATA_DIR

pd.options.mode.chained_assignment = None

dash.register_page(
    __name__,
    path="/costos/transform-oracle-mapping",
    title=PAGE_TITLE_PREFIX + "Transform Oracle Mapping",
)

PAGE_ID = "transform-oracle-mapping-"

# Ruta donde se persiste la tabla resultante como CSV
CSV_PATH = os.path.join(DATA_DIR, "transform_oracle_mapping.csv")


def _alert(msg, color, title):
    return dmc.Alert(msg, color=color, title=title, withCloseButton=True, mt="xs")


layout = dmc.Container(
    fluid=True,
    p="md",
    children=[
        dcc.Store(id=f"{PAGE_ID}data-store"),
        dcc.Download(id=f"{PAGE_ID}download"),
        Row([
            Column([
                dmc.Group(
                    mb="xs",
                    children=[
                        DashIconify(icon="tabler:table-import", width=26, color="#228be6"),
                        dmc.Title("Transform Oracle Mapping", order=2),
                    ],
                ),
                dmc.Text(
                    "Sube el Excel de solicitud de pedidos para mapear los IDs internos "
                    "de Oracle (item, actividad, class, department y linea de negocio). "
                    "La tabla resultante se guarda en data/transform_oracle_mapping.csv.",
                    size="sm", c="dimmed",
                ),
            ], size=12),
        ]),
        Row([
            Column([
                dcc.Upload(
                    id=f"{PAGE_ID}upload",
                    children=html.Div([
                        DashIconify(icon="mdi:file-excel", width=24),
                        html.Span(" Arrastra o selecciona el archivo Excel",
                                  style={"marginLeft": "8px"}),
                    ]),
                    style={
                        "height": "60px", "lineHeight": "60px",
                        "borderWidth": "1px", "borderStyle": "dashed",
                        "borderRadius": "5px", "textAlign": "center",
                        "margin": "10px 0",
                    },
                    multiple=False,
                    accept=".xlsx,.xls",
                ),
                dcc.Loading(
                    type="dot", color="#228be6",
                    children=html.Div(id=f"{PAGE_ID}status"),
                ),
            ], size=12),
        ]),
        Row([
            Column([
                dmc.Group(
                    justify="space-between", mb="sm",
                    children=[
                        html.Div(id=f"{PAGE_ID}shape-info"),
                        dmc.Button(
                            "DESCARGAR CSV",
                            id=f"{PAGE_ID}btn-csv",
                            color="green", variant="filled",
                            leftSection=DashIconify(icon="mdi:file-delimited"),
                            disabled=True,
                        ),
                    ],
                ),
                dcc.Loading(
                    type="circle", color="#228be6",
                    children=html.Div(id=f"{PAGE_ID}table", style={"minHeight": "200px"}),
                ),
            ], size=12),
        ]),
    ],
)


@callback(
    Output(f"{PAGE_ID}table", "children"),
    Output(f"{PAGE_ID}shape-info", "children"),
    Output(f"{PAGE_ID}status", "children"),
    Output(f"{PAGE_ID}data-store", "data"),
    Output(f"{PAGE_ID}btn-csv", "disabled"),
    Input(f"{PAGE_ID}upload", "contents"),
    State(f"{PAGE_ID}upload", "filename"),
    prevent_initial_call=True,
)
def process_excel(contents, filename):
    if not contents:
        return no_update, no_update, no_update, no_update, True

    try:
        _, content_string = contents.split(",", 1)
        decoded = base64.b64decode(content_string)
        df_input = pd.read_excel(io.BytesIO(decoded))
    except Exception as e:
        return None, None, _alert(f"Error leyendo el archivo: {e}", "red", "Error"), no_update, True

    try:
        df = transform_oracle_mapping(df_input)
    except KeyError as e:
        return None, None, _alert(str(e), "red", "Estructura invalida"), no_update, True
    except Exception as e:
        return None, None, _alert(f"Error procesando: {e}", "red", "Error"), no_update, True

    # Persistir la tabla resultante como CSV
    try:
        df.to_csv(CSV_PATH, index=False, encoding="utf-8-sig")
        saved_msg = f"Guardado en {os.path.relpath(CSV_PATH)}"
    except Exception as e:
        saved_msg = f"No se pudo guardar el CSV: {e}"

    col_defs = [
        {"field": c, "headerName": c, "sortable": True, "filter": True,
         "resizable": True, "minWidth": 90, "maxWidth": 320}
        for c in df.columns
    ]
    table = AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={"sortable": True, "filter": True, "resizable": True},
        dashGridOptions={
            "pagination": True, "paginationPageSize": 50,
            "animateRows": True, "suppressCellFocus": True,
            "rowHeight": 34, "headerHeight": 36,
        },
        style={"height": "480px", "width": "100%"},
        className="ag-theme-balham",
    )

    shape_info = dmc.Group(gap="xs", children=[
        dmc.Text("Resultado", fw=600, size="sm"),
        dmc.Badge(f"{df.shape[0]:,} filas", color="blue", variant="light", size="sm"),
        dmc.Badge(f"{df.shape[1]} cols", color="gray", variant="light", size="sm"),
    ])

    status = _alert(
        f"{filename}: {df.shape[0]:,} filas procesadas. {saved_msg}",
        "green", "Listo",
    )

    return table, shape_info, status, df.to_dict("records"), False


@callback(
    Output(f"{PAGE_ID}download", "data"),
    Input(f"{PAGE_ID}btn-csv", "n_clicks"),
    State(f"{PAGE_ID}data-store", "data"),
    prevent_initial_call=True,
)
def download_csv(n_clicks, data):
    if not data:
        return no_update
    df = pd.DataFrame(data)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return dcc.send_data_frame(
        df.to_csv, f"transform_oracle_mapping_{ts}.csv",
        index=False, encoding="utf-8-sig",
    )
