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
import unicodedata

pd.options.mode.chained_assignment = None

dash.register_page(__name__, "/apg/pagos_proveedores", title=PAGE_TITLE_PREFIX + "TXT Pagos Proveedores")
app = dash.get_app()
PAGE_ID = "pagos_proveedores-"


# ── Reglas de transformación ────────────────────────────────────────────────
# Las observaciones del banco sobre el archivo de "Pagos Globales a Proveedores":
#   1. El código "TRANSD" (Transferencia de Fondos) no es aceptado -> reemplazar por "1".
#   2. El tipo de cuenta bancaria (2º carácter del registro) se MANTIENE tal como lo
#      entrega ORACLE. Existen tres dígitos posibles: "A" = Cuenta Ahorro,
#      "B" = Cuenta Interbancaria, "C" = Cuenta Corriente. No se fuerza ninguna conversión.
#   3. Los nombres de los proveedores deben ir sin tildes (se eliminan los acentos).
#   4. Las filas de DETALLE deben quedar alineadas: el campo de monto (último campo)
#      se empuja al borde derecho rellenando con espacios entre el nombre y el monto,
#      hasta el ancho de la fila de detalle más larga del archivo.
# La línea de CABECERA (empieza con "1") no se rellena (solo se quitan espacios sobrantes).
TRANSD_CODE = "TRANSD"
TRANSD_REPLACEMENT = "1"


def strip_accents(text):
    """Elimina tildes/acentos preservando el largo (á→a, é→e, ñ→n, ü→u)."""
    nfkd = unicodedata.normalize("NFKD", text)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def transform_line(raw_line):
    """Limpia/transforma el contenido de una línea (sin ajustar ancho).
    Devuelve (línea, n_transd, n_tildes)."""
    clean = raw_line.rstrip("\r")
    n_transd = 0
    n_tildes = 0

    # Solo registros de detalle
    if clean.startswith("2"):
        # Modalidad de pago: "TRANSD" -> "1"
        # (el dígito de cuenta bancaria A/B/C se conserva intacto)
        if TRANSD_CODE in clean:
            n_transd = clean.count(TRANSD_CODE)
            clean = clean.replace(TRANSD_CODE, TRANSD_REPLACEMENT)

    # Quitar tildes/acentos (nombres de proveedores). Preserva el largo.
    sin_tildes = strip_accents(clean)
    if sin_tildes != clean:
        n_tildes = sum(1 for a, b in zip(clean, sin_tildes) if a != b)
    clean = sin_tildes

    return clean, n_transd, n_tildes


def align_detail(line, width):
    """Empuja el último campo (monto) al borde derecho hasta 'width' caracteres,
    rellenando con espacios entre el nombre del proveedor y el monto."""
    stripped = line.rstrip()
    parts = stripped.rsplit(None, 1)  # separa solo en el último bloque de espacios
    if len(parts) == 2:
        prefix, amount = parts
        n_spaces = width - len(prefix) - len(amount)
        if n_spaces < 1:
            n_spaces = 1  # al menos un separador
        return prefix + (" " * n_spaces) + amount
    return stripped.ljust(width)


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
        cleaned = []
        total_transd = 0
        total_tildes = 0

        for raw in lines:
            new_line, n_transd, n_tildes = transform_line(raw)
            total_transd += n_transd
            total_tildes += n_tildes
            cleaned.append(new_line)

        # Ancho objetivo = fila de DETALLE más larga (registros que empiezan con "2")
        detail_widths = [len(l) for l in cleaned if l.startswith("2")]
        target_width = max(detail_widths) if detail_widths else 0

        out_lines = []
        for l in cleaned:
            if l.startswith("2"):
                # Detalle: monto alineado al borde derecho (ancho fijo)
                out_lines.append(align_detail(l, target_width))
            else:
                # Cabecera / otras líneas: sin relleno, solo quitar espacios sobrantes
                out_lines.append(l.rstrip())

        # Reconstruir con CRLF (formato bancario), preservando estructura/última línea
        content = "\r\n".join(out_lines)

        stats = {
            "filename": original_filename,
            "transd": total_transd,
            "tildes": total_tildes,
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
                    "se eliminan tildes de los nombres y todas las filas se ajustan a 179 caracteres. "
                    "El tipo de cuenta (A/B/C) se conserva tal como lo entrega ORACLE.",
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
    total_tildes = sum(s["tildes"] for s in all_stats)
    detalle = " · ".join(
        f"{s['filename']}: {s['lineas']} líneas, TRANSD→1: {s['transd']}, tildes eliminadas: {s['tildes']}"
        for s in all_stats
    )

    status = dmc.Alert(
        children=[
            dmc.Text(
                f"{len(processed_files)} archivo(s) procesado(s). "
                f"Total reemplazos TRANSD→1: {total_transd} | Tildes eliminadas: {total_tildes} | Montos alineados al borde derecho",
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
