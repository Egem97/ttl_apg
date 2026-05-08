import io
import base64
import time
import dash
import pandas as pd
import dash_mantine_components as dmc
from dash_iconify import DashIconify
from dash import html, dcc, callback, Input, Output, State, no_update
from dash_ag_grid import AgGrid
from datetime import date as _date

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph,
    Spacer, PageBreak, KeepTogether,
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
from helpers.files import load_data_agritracer


pd.options.mode.chained_assignment = None


dash.register_page(__name__, "/apg/transporte-agri", title=PAGE_TITLE_PREFIX + "Transportes match")
app = dash.get_app()
PAGE_ID = "transporte-agri-"


AGRI_COLUMNS = ["DOCUMENTO", "EMPRESA", "FECHA","FUNDO", "TRABAJADOR","ACTIVIDAD","PARTIDA PRESUPUESTARIA","MACRO PARTIDA"]
EXCEL_DNI_COL = "DNI"
EXCEL_FECHA_COL = "Fecha Registro"


def _normalize_dni(series: pd.Series) -> pd.Series:
    s = series.astype(str).str.strip()
    s = s.str.replace(r"\.0$", "", regex=True)
    s = s.str.replace(r"\D", "", regex=True)
    s = s.replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return s


def _normalize_fecha(series: pd.Series) -> pd.Series:
    """Devuelve strings 'YYYY-MM-DD' (o pd.NA) para que el merge siempre compare el mismo tipo."""
    if pd.api.types.is_datetime64_any_dtype(series):
        dt = pd.to_datetime(series, errors="coerce")
        return dt.dt.strftime("%Y-%m-%d").where(dt.notna(), other=pd.NA)

    s = series.astype(str).str.strip()
    # Elimina componente de hora: "2026-01-15T00:00:00" o "2026-01-15 00:00:00" → "2026-01-15"
    s = s.str.split(r"[ T]").str[0]
    s = s.str.replace("-", "/", regex=False)

    # Intento 1: DD/MM/YYYY (formato típico de exports bancarios/peruanos)
    dt = pd.to_datetime(s, format="%d/%m/%Y", errors="coerce")
    # Intento 2: YYYY/MM/DD (formato ISO que llega desde dcc.Store)
    mask = dt.isna() & s.notna() & ~s.isin({"nan", "None", ""})
    if mask.any():
        dt.loc[mask] = pd.to_datetime(s[mask], format="%Y/%m/%d", errors="coerce")
    # Intento 3: parseo genérico para cualquier otro formato
    mask2 = dt.isna() & s.notna() & ~s.isin({"nan", "None", ""})
    if mask2.any():
        dt.loc[mask2] = pd.to_datetime(s[mask2], errors="coerce")

    return dt.dt.strftime("%Y-%m-%d").where(dt.notna(), other=pd.NA)


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
                                            dmc.Button(
                                                "DESCARGAR MANIFIESTO PDF",
                                                id=f"{PAGE_ID}btn-pdf",
                                                color="red",
                                                variant="filled",
                                                leftSection=DashIconify(icon="mdi:file-pdf-box"),
                                                disabled=True,
                                            ),
                                        ],
                                        mt="md",
                                    ),
                                    dcc.Download(id=f"{PAGE_ID}download-xlsx"),
                                    dcc.Download(id=f"{PAGE_ID}download-pdf"),
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
    Output(f"{PAGE_ID}btn-pdf", "disabled"),
    Input(f"{PAGE_ID}upload-excel", "contents"),
    Input(f"{PAGE_ID}agritracer-store", "data"),
    State(f"{PAGE_ID}upload-excel", "filename"),
    prevent_initial_call=True,
)
def process_excel_and_merge(contents, agri_data, filename):
    if not contents:
        return no_update, no_update, no_update, True, True

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
            True,
        )

    df_agri = pd.DataFrame(agri_data)
    for col in AGRI_COLUMNS:
        if col not in df_agri.columns:
            df_agri[col] = pd.NA

    df_excel["_dni_key"] = _normalize_dni(df_excel[EXCEL_DNI_COL]).astype(str)
    df_excel["_fecha_key"] = _normalize_fecha(df_excel[EXCEL_FECHA_COL]).astype(str)
    print(df_agri.columns)
    df_agri["_dni_key"] = _normalize_dni(df_agri["DOCUMENTO"]).astype(str)
    df_agri["_fecha_key"] = _normalize_fecha(df_agri["FECHA"]).astype(str)
    df_agri_match = (
        df_agri[["_dni_key", "_fecha_key", "EMPRESA","FUNDO", "TRABAJADOR","ACTIVIDAD","PARTIDA PRESUPUESTARIA","MACRO PARTIDA"]]
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

    return table, df_merged.to_dict("records"), status, False, False


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
    cols = list(df.columns)
    n_rows = len(df)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Transportes", startrow=1)
        wb  = writer.book
        ws  = writer.sheets["Transportes"]

        # ── Formatos ──────────────────────────────────────────────────────────
        header_fmt = wb.add_format({
            "bold": True, "font_name": "Calibri", "font_size": 11,
            "font_color": "#FFFFFF", "bg_color": "#1B4F72",
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#FFFFFF",
        })
        row_even_fmt = wb.add_format({
            "font_name": "Calibri", "font_size": 10,
            "bg_color": "#FFFFFF", "valign": "vcenter",
            "border": 1, "border_color": "#D5D8DC",
        })
        row_odd_fmt = wb.add_format({
            "font_name": "Calibri", "font_size": 10,
            "bg_color": "#EBF5FB", "valign": "vcenter",
            "border": 1, "border_color": "#D5D8DC",
        })
        si_fmt = wb.add_format({
            "font_name": "Calibri", "font_size": 10, "bold": True,
            "font_color": "#1E8449", "bg_color": "#D5F5E3",
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#D5D8DC",
        })
        no_fmt = wb.add_format({
            "font_name": "Calibri", "font_size": 10, "bold": True,
            "font_color": "#922B21", "bg_color": "#FADBD8",
            "align": "center", "valign": "vcenter",
            "border": 1, "border_color": "#D5D8DC",
        })
        title_fmt = wb.add_format({
            "bold": True, "font_name": "Calibri", "font_size": 13,
            "font_color": "#1B4F72", "valign": "vcenter",
        })

        # ── Título en fila 0 ──────────────────────────────────────────────────
        ws.merge_range(0, 0, 0, max(len(cols) - 1, 0), "Transportes × Agritracer", title_fmt)
        ws.set_row(0, 22)

        # ── Cabeceras (fila 1, ya escritas por to_excel — las repintamos) ─────
        match_col_idx = cols.index("MATCH_AGRITRACER") if "MATCH_AGRITRACER" in cols else -1
        ws.set_row(1, 20)
        for ci, col in enumerate(cols):
            ws.write(1, ci, col, header_fmt)

        # ── Filas de datos ────────────────────────────────────────────────────
        for ri, row in enumerate(df.itertuples(index=False), start=2):
            base_fmt = row_even_fmt if ri % 2 == 0 else row_odd_fmt
            ws.set_row(ri, 16)
            for ci, val in enumerate(row):
                cell_val = "" if (val is None or (isinstance(val, float) and pd.isna(val))) else val
                if ci == match_col_idx:
                    ws.write(ri, ci, cell_val, si_fmt if cell_val == "SI" else no_fmt)
                else:
                    ws.write(ri, ci, cell_val, base_fmt)

        # ── Anchos de columna ─────────────────────────────────────────────────
        for ci, col in enumerate(cols):
            content_max = df[col].astype(str).map(len).max() if n_rows else 0
            col_width = min(max(content_max, len(col)) + 2, 45)
            ws.set_column(ci, ci, col_width)

        # ── Freeze cabecera + autofiltro ──────────────────────────────────────
        ws.freeze_panes(2, 0)
        ws.autofilter(1, 0, n_rows + 1, len(cols) - 1)

        # ── Tab color ─────────────────────────────────────────────────────────
        ws.set_tab_color("#1B4F72")

    base = (original_filename or "transportes").rsplit(".", 1)[0]
    filename = f"{base}_agritracer_{int(time.time())}.xlsx"
    return dcc.send_bytes(output.getvalue(), filename=filename)


# ── Estilos PDF ────────────────────────────────────────────────────────────────
_AZUL     = colors.HexColor("#1B4F72")
_AZUL_CLR = colors.HexColor("#D6EAF8")
_GRIS_CLR = colors.HexColor("#F2F3F4")
_NEGRO    = colors.black
_BLANCO   = colors.white

_sty_title   = ParagraphStyle("title",   fontName="Helvetica-Bold", fontSize=13, alignment=TA_CENTER, textColor=_AZUL,  spaceAfter=2)
_sty_subtitl = ParagraphStyle("subtitl", fontName="Helvetica-Bold", fontSize=10, alignment=TA_CENTER, textColor=_AZUL,  spaceAfter=6)
_sty_fecha   = ParagraphStyle("fecha",   fontName="Helvetica",      fontSize=8,  alignment=TA_RIGHT,  spaceAfter=0)
_sty_cell    = ParagraphStyle("cell",    fontName="Helvetica",      fontSize=7.5, leading=10)
_sty_cell_b  = ParagraphStyle("cell_b",  fontName="Helvetica-Bold", fontSize=7.5, leading=10)

_ROWS_PER_PAGE = 24


def _val(row: dict, key: str) -> str:
    v = row.get(key, "")
    return "" if (v is None or (isinstance(v, float) and pd.isna(v))) else str(v)


def _info_table(row: dict) -> Table:
    """Tabla de encabezado del manifiesto (empresa, ruta, placa, conductor…)."""
    W = 17 * cm
    data = [
        [Paragraph(f"<b>EMPRESA:</b> {_val(row, 'Proveedor')}", _sty_cell)],
        [Paragraph(f"<b>RUTA:</b> {_val(row, 'Ruta')}", _sty_cell)],
        [Paragraph(f"<b>PLACA DEL VEHÍCULO:</b> {_val(row, 'Placa')}    "
                   f"<b>FECHA:</b> {_val(row, 'Fecha')}", _sty_cell)],
        [Paragraph(f"<b>CONDUCTOR:</b> {_val(row, 'Conductor')}    "
                   f"<b>LC:</b> {_val(row, 'LC')}    "
                   f"<b>DNI:</b> {_val(row, 'DNI Conductor')}", _sty_cell)],
    ]
    tbl = Table(data, colWidths=[W])
    tbl.setStyle(TableStyle([
        ("BOX",         (0, 0), (-1, -1), 0.5, _NEGRO),
        ("INNERGRID",   (0, 0), (-1, -1), 0.3, colors.HexColor("#BDC3C7")),
        ("BACKGROUND",  (0, 0), (-1, 0),  _AZUL_CLR),
        ("BACKGROUND",  (0, 1), (-1, 1),  _AZUL_CLR),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING",(0,0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]))
    return tbl


def _passenger_table(rows: list[dict], start_n: int) -> Table:
    """Tabla de pasajeros con N°, nombre, DNI y columnas de Agritracer."""
    col_widths = [1*cm, 5.5*cm, 2.5*cm, 3*cm, 3*cm, 2*cm]
    header = [
        Paragraph("<b>N°</b>",                           _sty_cell_b),
        Paragraph("<b>Nombres y Apellidos</b>",           _sty_cell_b),
        Paragraph("<b>DNI</b>",                           _sty_cell_b),
        Paragraph("<b>Actividad</b>",                     _sty_cell_b),
        Paragraph("<b>Partida Presupuestaria</b>",        _sty_cell_b),
        Paragraph("<b>Macro Partida</b>",                 _sty_cell_b),
    ]
    data = [header]
    for i, r in enumerate(rows, start=start_n):
        data.append([
            Paragraph(str(i),                              _sty_cell),
            Paragraph(_val(r, "AGRI_TRABAJADOR"),          _sty_cell),
            Paragraph(_val(r, "DNI"),                      _sty_cell),
            Paragraph(_val(r, "ACTIVIDAD"),                _sty_cell),
            Paragraph(_val(r, "PARTIDA PRESUPUESTARIA"),   _sty_cell),
            Paragraph(_val(r, "MACRO PARTIDA"),            _sty_cell),
        ])

    n = len(data)
    tbl = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ("BOX",           (0, 0), (-1, -1), 0.5, _NEGRO),
        ("INNERGRID",     (0, 0), (-1, -1), 0.3, colors.HexColor("#BDC3C7")),
        ("BACKGROUND",    (0, 0), (-1, 0),  _AZUL),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  _BLANCO),
        ("ALIGN",         (0, 0), (-1, 0),  "CENTER"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",    (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
        ("LEFTPADDING",   (0, 0), (-1, -1), 3),
    ]
    for row_i in range(1, n):
        bg = _GRIS_CLR if row_i % 2 == 0 else _BLANCO
        style.append(("BACKGROUND", (0, row_i), (-1, row_i), bg))
    tbl.setStyle(TableStyle(style))
    return tbl


def _build_manifiesto_pdf(df_matched: pd.DataFrame) -> bytes:
    """Genera el PDF de manifiesto masivo agrupado por Proveedor + AGRI_EMPRESA."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=1.5*cm, rightMargin=1.5*cm,
        topMargin=1.5*cm,  bottomMargin=1.5*cm,
    )

    today = _date.today().strftime("%d/%m/%Y")
    story = []

    group_cols = [c for c in ["Proveedor", "AGRI_EMPRESA"] if c in df_matched.columns]
    if not group_cols:
        groups = [("", df_matched)]
    else:
        groups = list(df_matched.groupby(group_cols, sort=False))
        # groupby devuelve tupla de keys cuando hay varios; normalizamos
        groups = [(k if isinstance(k, tuple) else (k,), g) for k, g in groups]

    first_group = True
    for keys, gdf in groups:
        if not first_group:
            story.append(PageBreak())
        first_group = False

        proveedor  = keys[0] if len(keys) > 0 else ""
        agri_emp   = keys[1] if len(keys) > 1 else (gdf["AGRI_EMPRESA"].iloc[0] if "AGRI_EMPRESA" in gdf.columns else "")
        first_row  = gdf.iloc[0].to_dict()
        rows_list  = gdf.to_dict("records")

        # ── Encabezado de página ──────────────────────────────────────────────
        def _page_header(proveedor=proveedor, agri_emp=agri_emp, first_row=first_row, today=today):
            return [
                Paragraph(today, _sty_fecha),
                Paragraph(str(proveedor).upper(), _sty_title),
                Paragraph(f"MANIFIESTO DE PASAJEROS {str(agri_emp).upper()}", _sty_subtitl),
                _info_table(first_row),
                Spacer(1, 0.3*cm),
            ]

        # ── Paginación: _ROWS_PER_PAGE filas por página ───────────────────────
        chunks = [rows_list[i:i+_ROWS_PER_PAGE] for i in range(0, max(len(rows_list), 1), _ROWS_PER_PAGE)]
        for page_i, chunk in enumerate(chunks):
            if page_i > 0:
                story.append(PageBreak())
            story.extend(_page_header())
            story.append(_passenger_table(chunk, start_n=page_i * _ROWS_PER_PAGE + 1))

    doc.build(story)
    return buf.getvalue()


@callback(
    Output(f"{PAGE_ID}download-pdf", "data"),
    Input(f"{PAGE_ID}btn-pdf", "n_clicks"),
    State(f"{PAGE_ID}merged-store", "data"),
    State(f"{PAGE_ID}upload-excel", "filename"),
    prevent_initial_call=True,
)
def download_manifiesto_pdf(n_clicks, merged_data, original_filename):
    if not n_clicks or not merged_data:
        return no_update

    df = pd.DataFrame(merged_data)
    df_matched = df[df["MATCH_AGRITRACER"] == "SI"].copy()

    if df_matched.empty:
        return no_update

    pdf_bytes = _build_manifiesto_pdf(df_matched)
    base = (original_filename or "transportes").rsplit(".", 1)[0]
    filename = f"manifiesto_{base}_{int(time.time())}.pdf"
    return dcc.send_bytes(pdf_bytes, filename=filename)
