"""Transformaciones para el mapeo de IDs de Oracle (NetSuite) sobre el Excel
de solicitud de pedidos de costos.

Adaptado de ``transformer_mapping_oracle_id.py`` (ejemplo Streamlit) al patron
de helpers del proyecto. Lee los datasets de mapeo desde ``data/`` y realiza los
left joins sobre el DataFrame principal para agregar los IDs internos de Oracle.
"""

import os
import unicodedata

import pandas as pd

# Raiz del proyecto: helpers/transform/oracle_mapping.py -> subir 3 niveles
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
)

# Columnas que se seleccionan del Excel de entrada (ya normalizadas: sin tildes y MAYUS)
INPUT_COLUMNS = [
    "ID INTERNO", "NUMERO DE DOCUMENTO", "SUBSIDIARIA", "ARTICULO",
    "APG: ACTIVIDAD", "NOMBRE", "NOMBRE.1", "APG: LINEA DE NEGOCIO",
]

RENAME_MAP = {
    "ARTICULO": "ITEM",
    "APG: ACTIVIDAD": "ACTIVIDAD",
    "NOMBRE": "CLASS",
    "NOMBRE.1": "DEPARTMENT",
    "APG: LINEA DE NEGOCIO": "LINEA DE NEGOCIO",
}


def strip_accents(text) -> str:
    """Remueve diacriticos (tildes) usando descomposicion Unicode."""
    return "".join(
        c for c in unicodedata.normalize("NFKD", str(text)) if not unicodedata.combining(c)
    )


def _read_suiteql_banner(filename: str) -> pd.DataFrame:
    """Lee un export de NetSuite SuiteQL cuya primera fila es un banner
    ('NetSuite SuiteQL - N registros - N columnas') y cuyos encabezados
    reales estan en la segunda fila."""
    path = os.path.join(DATA_DIR, filename)
    df = pd.read_excel(path, skiprows=1)
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df


def load_linea_negocio() -> pd.DataFrame:
    """data/linea_negocio.xlsx -> ID_LINEANEG, LINEA DE NEGOCIO."""
    path = os.path.join(DATA_DIR, "linea_negocio.xlsx")
    df = pd.read_excel(path)
    df.columns = [strip_accents(col).strip().upper() for col in df.columns]
    df = df.rename(columns={"ID INTERNO": "ID_LINEANEG", "NOMBRE": "LINEA DE NEGOCIO"})
    return df


def load_actividad() -> pd.DataFrame:
    """data/suiteql_actividad.xlsx -> actividad, id_actividad, id_macropartida,
    id_partida_pre, macropartida, partida_presupuestaria."""
    path = os.path.join(DATA_DIR, "suiteql_actividad.xlsx")
    df = pd.read_excel(path)
    df.columns = [str(col).strip().upper() for col in df.columns]
    return df


def load_class() -> pd.DataFrame:
    """data/suiteql_class.xlsx -> ID_CLASS, CLASS."""
    df = _read_suiteql_banner("suiteql_class.xlsx")
    df = df[["ID", "NAME"]]
    df = df.rename(columns={"ID": "ID_CLASS", "NAME": "CLASS"})
    return df


def load_department() -> pd.DataFrame:
    """data/suiteql_department.xlsx -> ID_DEPARTMENT, DEPARTMENT."""
    df = _read_suiteql_banner("suiteql_department.xlsx")
    df = df[["FULLNAME", "ID"]]
    df = df.rename(columns={"ID": "ID_DEPARTMENT", "FULLNAME": "DEPARTMENT"})
    return df


def load_item() -> pd.DataFrame:
    """data/suiteql_item.xlsx -> ID_ITEM, ITEM."""
    path = os.path.join(DATA_DIR, "suiteql_item.xlsx")
    df = pd.read_excel(path)
    df.columns = [str(col).strip().upper() for col in df.columns]
    df = df.rename(columns={"ID": "ID_ITEM", "FULLNAME": "ITEM"})
    df = df[["ID_ITEM", "ITEM"]]
    return df


def transform_oracle_mapping(df_input: pd.DataFrame) -> pd.DataFrame:
    """Aplica la normalizacion, seleccion, renombrado y los left joins con los
    datasets de mapeo para agregar los IDs internos de Oracle.

    Levanta ``KeyError`` (via _validate) si faltan columnas requeridas.
    """
    df = df_input.copy()
    df.columns = [strip_accents(col).strip().upper() for col in df.columns]

    missing = [c for c in INPUT_COLUMNS if c not in df.columns]
    if missing:
        raise KeyError(f"Faltan columnas en el Excel: {', '.join(missing)}")

    df = df[INPUT_COLUMNS]
    df = df.rename(columns=RENAME_MAP)

    df = df.merge(load_item(),          on="ITEM",             how="left")
    df = df.merge(load_actividad(),     on="ACTIVIDAD",        how="left")
    df = df.merge(load_class(),         on="CLASS",            how="left")
    df = df.merge(load_department(),    on="DEPARTMENT",       how="left")
    df = df.merge(load_linea_negocio(), on="LINEA DE NEGOCIO", how="left")

    return df
