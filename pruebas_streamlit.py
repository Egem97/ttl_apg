import streamlit as st

from helpers.get_token import get_access_token
from helpers.get_api import listar_archivos_en_carpeta_compartida
from helpers.helpers import get_download_url_by_name


DRIVE_ID_COSTOS_PACKING = "b!DKrRhqg3EES4zcUVZUdhr281sFZAlBZDuFVNPqXRguBl81P5QY7KRpUL2n3RaODo"
ITEM_ID_COSTOS_PACKING = "01PNBE7BDDPRCTEUCL5ZFLQCKHUA4RJAF2"
access_token = get_access_token()

url_ = listar_archivos_en_carpeta_compartida(
    access_token,
    DRIVE_ID_COSTOS_PACKING,
    ITEM_ID_COSTOS_PACKING
)

st.write(get_download_url_by_name(url_,"KG PPTO.xlsx"))   