import io
import math
import pandas as pd
import dash
from dash import dcc, html, Input, Output, State, callback, no_update
import dash_mantine_components as dmc
from dash_ag_grid import AgGrid
from dash_iconify import DashIconify
import requests
from requests_oauthlib import OAuth1

from constants import PAGE_TITLE_PREFIX
from helpers.config import load_config

config = load_config()

dash.register_page(
    __name__,
    path="/apg/consultapg",
    title=PAGE_TITLE_PREFIX + "Consulta",
)

PAGE_ID = "consultas-"
_oracle = config.get("oracle", {})
_realm = _oracle.get("realm", "")
PROD_URL = _oracle.get("url", "")
SB_URL = PROD_URL.replace(f"{_realm}.suitetalk", f"{_realm}-sb1.suitetalk")
SB_REALM = f"{_realm}_SB1"


def _build_oauth(realm: str) -> OAuth1:
    return OAuth1(
        client_key=_oracle["client_key"],
        client_secret=_oracle["client_secret"],
        resource_owner_key=_oracle["resource_owner_key"],
        resource_owner_secret=_oracle["resource_owner_secret"],
        realm=realm,
        signature_method="HMAC-SHA256",
    )


def _run_suiteql(query: str, url: str, oauth: OAuth1) -> list:
    payload = {"q": query}
    headers = {"Prefer": "transient", "Content-Type": "application/json"}
    all_items = []
    while url:
        resp = requests.post(url, auth=oauth, json=payload, headers=headers)
        if resp.status_code != 200:
            raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:500]}")
        data = resp.json()
        all_items.extend(data.get("items", []))
        next_link = next((l for l in data.get("links", []) if l["rel"] == "next"), None)
        url = next_link["href"] if next_link else None
    return all_items


def _safe_val(v):
    """Convierte NaN/Inf a cadena vacía para que xlsxwriter no falle."""
    if v is None:
        return ""
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return ""
    return v


_OVERLAY_HIDDEN = {"display": "none"}
_OVERLAY_VISIBLE = {
    "display": "flex",
    "position": "fixed",
    "top": 0, "left": 0,
    "width": "100vw", "height": "100vh",
    "backgroundColor": "rgba(10, 15, 35, 0.55)",
    "backdropFilter": "blur(4px)",
    "WebkitBackdropFilter": "blur(4px)",
    "zIndex": 9999,
    "alignItems": "center",
    "justifyContent": "center",
    "flexDirection": "column",
    "gap": "16px",
    "pointerEvents": "all",
}


def _build_df(store: dict) -> pd.DataFrame:
    """Reconstruye el DataFrame respetando el orden de columnas guardado."""
    col_order = store["col_order"]
    df = pd.DataFrame(store["rows"], columns=col_order)
    scalar_cols = [
        c for c in col_order
        if not df[c].apply(lambda v: isinstance(v, (list, dict))).any()
    ]
    return df[scalar_cols]


layout = dmc.Container(
    fluid=True,
    p="md",
    children=[
        dcc.Store(id=f"{PAGE_ID}data-store"),
        dcc.Download(id=f"{PAGE_ID}download"),

        # ── Overlay de carga full-viewport ───────────────────────────────────
        html.Div(
            id=f"{PAGE_ID}overlay",
            style=_OVERLAY_HIDDEN,
            children=[
                dmc.Loader(size="xl", color="white", type="oval"),
                dmc.Text(
                    "Ejecutando query...",
                    c="white",
                    fw=500,
                    size="lg",
                    style={"letterSpacing": "0.3px"},
                ),
            ],
        ),

        dmc.Group(
            mb="lg",
            children=[
                DashIconify(icon="tabler:database-search", width=26, color="#228be6"),
                dmc.Title("NetSuite SuiteQL Query", order=3),
            ],
        ),

        dmc.Grid(
            gutter="md",
            align="stretch",
            children=[

                # ── Panel izquierdo: query ───────────────────────────────────
                dmc.GridCol(
                    span={"base": 12, "md": 4},
                    children=[
                        dmc.Paper(
                            p="md",
                            withBorder=True,
                            radius="md",
                            h="100%",
                            children=[
                                dmc.Text("Query Settings", fw=600, size="sm", c="dimmed", mb="sm"),
                                html.Div(
                                    style={"marginBottom": "12px"},
                                    children=[
                                        dmc.Text("SuiteQL Query", size="sm", fw=500, mb=4),
                                        dcc.Textarea(
                                            id=f"{PAGE_ID}query-input",
                                            placeholder="SELECT id, tranid, type\nFROM transaction\nWHERE ...",
                                            style={
                                                "width": "100%",
                                                "minHeight": "280px",
                                                "resize": "vertical",
                                                "fontFamily": "Consolas, 'Courier New', monospace",
                                                "fontSize": "13px",
                                                "padding": "10px 12px",
                                                "border": "1px solid #ced4da",
                                                "borderRadius": "6px",
                                                "outline": "none",
                                                "lineHeight": "1.5",
                                                "color": "#212529",
                                                "backgroundColor": "#fdfdfd",
                                                "boxSizing": "border-box",
                                            },
                                        ),
                                    ],
                                ),
                                dmc.Select(
                                    id=f"{PAGE_ID}environment",
                                    label="Ambiente",
                                    data=[
                                        {"value": "production", "label": "Production"},
                                        # {"value": "sandbox", "label": "Sandbox"},
                                    ],
                                    value="production",
                                    mb="md",
                                    size="sm",
                                    leftSection=DashIconify(icon="tabler:server", width=16),
                                ),
                                dmc.Button(
                                    "Ejecutar Query",
                                    id=f"{PAGE_ID}run-btn",
                                    leftSection=DashIconify(icon="tabler:player-play", width=16),
                                    color="blue",
                                    fullWidth=True,
                                    size="sm",
                                    loading=False,
                                ),
                                dmc.Space(h="sm"),
                                html.Div(id=f"{PAGE_ID}status-msg"),
                            ],
                        )
                    ],
                ),

                # ── Panel derecho: resultados ────────────────────────────────
                dmc.GridCol(
                    span={"base": 12, "md": 8},
                    children=[
                        dmc.Paper(
                            p="md",
                            withBorder=True,
                            radius="md",
                            children=[
                                dmc.Group(
                                    justify="space-between",
                                    mb="sm",
                                    children=[
                                        html.Div(id=f"{PAGE_ID}shape-info"),
                                        dmc.Button(
                                            "Descargar Excel",
                                            id=f"{PAGE_ID}download-btn",
                                            leftSection=DashIconify(icon="tabler:file-spreadsheet", width=15),
                                            color="teal",
                                            variant="subtle",
                                            size="xs",
                                            disabled=True,
                                        ),
                                    ],
                                ),
                                dcc.Loading(
                                    type="circle",
                                    color="#228be6",
                                    children=html.Div(
                                        id=f"{PAGE_ID}results-container",
                                        style={"minHeight": "80px"},
                                    ),
                                ),
                            ],
                        )
                    ],
                ),
            ],
        ),
    ],
)


# Activa el loading del botón y muestra el overlay inmediatamente al hacer click
dash.clientside_callback(
    "function(n) { return true; }",
    Output(f"{PAGE_ID}run-btn", "loading", allow_duplicate=True),
    Input(f"{PAGE_ID}run-btn", "n_clicks"),
    prevent_initial_call=True,
)

dash.clientside_callback(
    """function(n) {
        return {
            display: 'flex', position: 'fixed',
            top: 0, left: 0, width: '100vw', height: '100vh',
            backgroundColor: 'rgba(10,15,35,0.55)',
            backdropFilter: 'blur(4px)', WebkitBackdropFilter: 'blur(4px)',
            zIndex: 9999, alignItems: 'center', justifyContent: 'center',
            flexDirection: 'column', gap: '16px', pointerEvents: 'all'
        };
    }""",
    Output(f"{PAGE_ID}overlay", "style", allow_duplicate=True),
    Input(f"{PAGE_ID}run-btn", "n_clicks"),
    prevent_initial_call=True,
)


@callback(
    Output(f"{PAGE_ID}run-btn", "loading"),
    Output(f"{PAGE_ID}overlay", "style"),
    Output(f"{PAGE_ID}data-store", "data"),
    Output(f"{PAGE_ID}status-msg", "children"),
    Input(f"{PAGE_ID}run-btn", "n_clicks"),
    State(f"{PAGE_ID}query-input", "value"),
    State(f"{PAGE_ID}environment", "value"),
    prevent_initial_call=True,
)
def run_query(n_clicks, query, environment):
    if not query or not query.strip():
        return False, _OVERLAY_HIDDEN, no_update, dmc.Alert(
            "Ingresa una query SuiteQL.",
            color="yellow",
            icon=DashIconify(icon="tabler:alert-triangle"),
            withCloseButton=True,
            mt="xs",
        )

    url = PROD_URL if environment == "production" else SB_URL
    realm = _realm if environment == "production" else SB_REALM
    oauth = _build_oauth(realm)

    try:
        items = _run_suiteql(query.strip(), url, oauth)
        col_order = list(items[0].keys()) if items else []
        store = {"col_order": col_order, "rows": items}
        return False, _OVERLAY_HIDDEN, store, dmc.Alert(
            f"{len(items):,} registros obtenidos.",
            color="green",
            icon=DashIconify(icon="tabler:circle-check"),
            withCloseButton=True,
            mt="xs",
        )
    except Exception as exc:
        return False, _OVERLAY_HIDDEN, no_update, dmc.Alert(
            str(exc),
            title="Error",
            color="red",
            icon=DashIconify(icon="tabler:circle-x"),
            withCloseButton=True,
            mt="xs",
        )


@callback(
    Output(f"{PAGE_ID}results-container", "children"),
    Output(f"{PAGE_ID}shape-info", "children"),
    Output(f"{PAGE_ID}download-btn", "disabled"),
    Input(f"{PAGE_ID}data-store", "data"),
    prevent_initial_call=True,
)
def update_results(store):
    if not store or not store.get("rows"):
        return html.Div(), None, True

    df = _build_df(store)

    col_defs = [
        {
            "field": c,
            "headerName": c,
            "sortable": True,
            "filter": True,
            "resizable": True,
            "minWidth": 90,
            "maxWidth": 280,
        }
        for c in df.columns
    ]

    table = AgGrid(
        rowData=df.to_dict("records"),
        columnDefs=col_defs,
        defaultColDef={
            "sortable": True,
            "filter": True,
            "resizable": True,
            "suppressMovable": False,
        },
        dashGridOptions={
            "pagination": True,
            "paginationPageSize": 50,
            "animateRows": True,
            "suppressCellFocus": True,
            "rowHeight": 34,
            "headerHeight": 36,
        },
        style={"height": "480px", "width": "100%"},
        className="ag-theme-balham",
    )

    shape_info = dmc.Group(
        gap="xs",
        children=[
            dmc.Text("Resultados", fw=600, size="sm"),
            dmc.Badge(f"{df.shape[0]:,} filas", color="blue", variant="light", size="sm"),
            dmc.Badge(f"{df.shape[1]} cols", color="gray", variant="light", size="sm"),
        ],
    )

    return table, shape_info, False


@callback(
    Output(f"{PAGE_ID}download", "data"),
    Input(f"{PAGE_ID}download-btn", "n_clicks"),
    State(f"{PAGE_ID}data-store", "data"),
    prevent_initial_call=True,
)
def download_excel(n_clicks, store):
    if not store or not store.get("rows"):
        return no_update

    df = _build_df(store)

    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
        sheet = "Resultados"
        wb = writer.book
        ws = wb.add_worksheet(sheet)
        writer.sheets[sheet] = ws

        # ── Formatos ─────────────────────────────────────────────────────────
        fmt_title = wb.add_format({
            "bold": True, "font_name": "Calibri", "font_size": 13,
            "font_color": "#1C4E80",
        })
        fmt_header = wb.add_format({
            "bold": True, "font_name": "Calibri", "font_size": 10,
            "font_color": "#FFFFFF", "bg_color": "#1C4E80",
            "align": "center", "valign": "vcenter", "border": 0,
        })
        fmt_cell = wb.add_format({
            "font_name": "Calibri", "font_size": 10,
            "valign": "vcenter", "border": 0,
            "bottom": 1, "bottom_color": "#E9ECEF",
        })
        fmt_cell_alt = wb.add_format({
            "font_name": "Calibri", "font_size": 10,
            "valign": "vcenter", "border": 0,
            "bottom": 1, "bottom_color": "#E9ECEF",
            "bg_color": "#F8F9FA",
        })

        # ── Fila 0: título ────────────────────────────────────────────────────
        ws.write(0, 0, f"NetSuite SuiteQL  —  {df.shape[0]:,} registros  ·  {df.shape[1]} columnas", fmt_title)
        ws.set_row(0, 22)

        # ── Fila 1: headers ───────────────────────────────────────────────────
        for col_i, col_name in enumerate(df.columns):
            ws.write(1, col_i, col_name, fmt_header)
        ws.set_row(1, 20)

        # ── Filas de datos con alternancia y valores seguros ──────────────────
        for row_i, row in enumerate(df.itertuples(index=False), start=2):
            fmt = fmt_cell_alt if row_i % 2 == 0 else fmt_cell
            for col_i, val in enumerate(row):
                ws.write(row_i, col_i, _safe_val(val), fmt)

        # ── Ancho de columnas automático ──────────────────────────────────────
        for col_i, col_name in enumerate(df.columns):
            max_content = df[col_name].astype(str).str.len().max() if len(df) > 0 else 0
            ws.set_column(col_i, col_i, min(max(len(col_name), max_content) + 2, 40))

        ws.freeze_panes(2, 0)

    return dcc.send_bytes(buf.getvalue(), "suiteql_results.xlsx")
