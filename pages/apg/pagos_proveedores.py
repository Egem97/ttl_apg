import dash
import pandas as pd
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State
from dash_iconify import DashIconify
from components.grid import Row, Column
from constants import PAGE_TITLE_PREFIX
import base64
import io
import zipfile

pd.options.mode.chained_assignment = None

dash.register_page(__name__, "/apg/pagos_proveedores", title=PAGE_TITLE_PREFIX + "TXT Pagos Proveedores")
app = dash.get_app()
PAGE_ID = "pagos_proveedores-"


# ── Reglas de transformación ────────────────────────────────────────────────
# Las observaciones del banco sobre el archivo de "Pagos Globales a Proveedores":
#   1. El código "TRANSD" (Transferencia de Fondos) no es aceptado -> reemplazar por "1".
#   2. El tipo de cuenta figura como Cuenta Corriente ("C", 2º carácter del registro)
#      y debe registrarse como Cuenta Interbancaria ("B").
# Solo aplican a los registros de DETALLE (líneas que empiezan con "2").
# La línea de CABECERA (empieza con "1") no se modifica.
TRANSD_CODE = "TRANSD"
TRANSD_REPLACEMENT = "1"


def transform_line(raw_line):
    """Transforma una línea. Devuelve (línea_transformada, n_transd, cambio_cuenta)."""
    clean = raw_line.rstrip("\r")
    n_transd = 0
    cuenta_changed = False

    # Solo registros de detalle
    if clean.startswith("2"):
        # 1) Tipo de cuenta: Corriente (C) -> Interbancaria (B), únicamente el 2º carácter
        if len(clean) > 1 and clean[1] == "C":
            clean = clean[0] + "B" + clean[2:]
            cuenta_changed = True

        # 2) Modalidad de pago: "TRANSD" -> "1" (restaura además el ancho fijo del registro)
        if TRANSD_CODE in clean:
            n_transd = clean.count(TRANSD_CODE)
            clean = clean.replace(TRANSD_CODE, TRANSD_REPLACEMENT)

    return clean, n_transd, cuenta_changed


def process_file_content(content_string, original_filename):
    """Decodifica el contenido base64 de un .txt y aplica las transformaciones."""
    try:
        if "," in content_string:
            content_string = content_string.split(",", 1)[1]

        decoded = base64.b64decode(content_string)
        try:
            text = decoded.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = decoded.decode("latin-1")

        lines = text.split("\n")
        out_lines = []
        total_transd = 0
        total_cuenta = 0

        for raw in lines:
            new_line, n_transd, cuenta_changed = transform_line(raw)
            total_transd += n_transd
            total_cuenta += 1 if cuenta_changed else 0
            out_lines.append(new_line)

        # Reconstruir con CRLF (formato bancario), preservando estructura/última línea
        content = "\r\n".join(out_lines)

        stats = {
            "filename": original_filename,
            "transd": total_transd,
            "cuenta": total_cuenta,
            "lineas": sum(1 for l in out_lines if l),
        }
        return original_filename, content, stats
    except Exception as e:
        print(f"Error procesando {original_filename}: {e}")
        return None, None, None


def create_custom_layout():
    return dmc.Container(children=[
        Row([
            Column([
                #DashIconify(icon="mdi:bank-transfer", width=30),
                dmc.Title("Transformación TXT Pagos a Proveedores", order=2),
                dmc.Text(
                    "Sube de 1 a N archivos .txt. Se corrige: código TRANSD → 1, "
                    "y tipo de cuenta Corriente (C) → Interbancaria (B). La cabecera no se modifica.",
                    size="sm", c="dimmed", mb="sm",
                ),
            ], size=8),
            Column([
                dcc.Upload(
                    id=f"{PAGE_ID}upload",
                    children=html.Div(["Arrastra o ", html.A("Selecciona archivos .txt")]),
                    style={
                        "height": "60px",
                        "lineHeight": "60px",
                        "borderWidth": "1px",
                        "borderStyle": "dashed",
                        "borderRadius": "5px",
                        "textAlign": "center",
                        "margin": "10px",
                    },
                    multiple=True,
                    accept=".txt",
                ),
            ], size=4),
        ]),
        Row([
            Column([
                dmc.Textarea(
                    id=f"{PAGE_ID}preview",
                    label="Vista previa (primeras líneas del último archivo procesado)",
                    autosize=True,
                    minRows=6,
                    maxRows=12,
                    style={"fontFamily": "monospace"},
                ),
                html.Div(id=f"{PAGE_ID}status", style={"marginTop": "10px"}),
            ], size=12),
        ]),
        Row([
            Column([
                dmc.Group([
                    dmc.Button(
                        "Descargar procesados (.txt / .zip)",
                        id=f"{PAGE_ID}btn-download",
                        color="green",
                        leftSection=DashIconify(icon="mdi:download"),
                        disabled=True,
                    ),
                    dcc.Download(id=f"{PAGE_ID}download"),
                    dcc.Store(id=f"{PAGE_ID}store"),
                ], mb=10, mt="md"),
            ], size=12),
        ]),
    ], fluid=True)


layout = create_custom_layout()


@callback(
    Output(f"{PAGE_ID}preview", "value"),
    Output(f"{PAGE_ID}status", "children"),
    Output(f"{PAGE_ID}store", "data"),
    Output(f"{PAGE_ID}btn-download", "disabled"),
    Input(f"{PAGE_ID}upload", "contents"),
    State(f"{PAGE_ID}upload", "filename"),
    prevent_initial_call=True,
)
def update_output(list_of_contents, list_of_names):
    if not list_of_contents:
        return "", "", None, True

    processed_files = []
    last_preview = ""
    all_stats = []

    for c, n in zip(list_of_contents, list_of_names):
        new_name, content, stats = process_file_content(c, n)
        if new_name and content is not None:
            processed_files.append({"filename": new_name, "content": content})
            all_stats.append(stats)
            last_preview = "\n".join(content.splitlines()[:8])

    if not processed_files:
        return (
            "",
            dmc.Alert("No se pudieron procesar los archivos.", color="red", title="Error"),
            None,
            True,
        )

    total_transd = sum(s["transd"] for s in all_stats)
    total_cuenta = sum(s["cuenta"] for s in all_stats)
    detalle = " · ".join(
        f"{s['filename']}: {s['lineas']} líneas, TRANSD→1: {s['transd']}, C→B: {s['cuenta']}"
        for s in all_stats
    )

    status = dmc.Alert(
        children=[
            dmc.Text(
                f"{len(processed_files)} archivo(s) procesado(s). "
                f"Total reemplazos TRANSD→1: {total_transd} | Cuentas C→B: {total_cuenta}",
                fw=600,
            ),
            dmc.Text(detalle, size="xs", c="dimmed", mt=4),
        ],
        color="green",
        title="Transformación completada",
    )
    return last_preview, status, processed_files, False


@callback(
    Output(f"{PAGE_ID}download", "data"),
    Input(f"{PAGE_ID}btn-download", "n_clicks"),
    State(f"{PAGE_ID}store", "data"),
    prevent_initial_call=True,
)
def download_files(n_clicks, data):
    if not data:
        return None

    if len(data) == 1:
        f = data[0]
        return dict(content=f["content"], filename=f["filename"])

    output_zip = io.BytesIO()
    with zipfile.ZipFile(output_zip, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for item in data:
            zf.writestr(item["filename"], item["content"])
    output_zip.seek(0)
    return dcc.send_bytes(output_zip.read(), filename=f"pagos_proveedores_procesados_{len(data)}.zip")
