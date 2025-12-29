import requests
import time
import pandas as pd
import io
from pathlib import Path
from helpers.get_token import get_access_token, load_config 
from helpers.helpers import create_format_excel_in_memory

config = load_config()


BASE_URL = "https://api.apis.net.pe/v2/sunat/tipo-cambio"
TOKEN = "apis-token-16554.ZQM8MpXKbbVnqEaLmLByory531BrQp20"


def listar_archivos_en_carpeta_compartida(access_token: str  ,drive_id: str, item_id: str):
    """
    Lista los archivos dentro de una carpeta compartida en OneDrive / SharePoint usando Microsoft Graph.

    :param access_token: Token de acceso válido con permisos Files.Read.All
    :param drive_id: El ID del drive compartido
    :param item_id: El ID de la carpeta compartida
    :return: Lista de archivos o carpetas dentro de esa carpeta
    """
    
    url = f"https://graph.microsoft.com/v1.0/drives/{drive_id}/items/{item_id}/children"
    headers = {
        "Authorization": f"Bearer {access_token}"
    }

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return response.json().get("value", [])
    else:
        print("❌ Error al obtener archivos:", response.status_code)
        print(response.json())
        return []




        


def get_tc_sunat_diario(date=None):
        headers = {
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/json"
        }

        params = {"date": date}
        response = requests.get(
            BASE_URL,
            headers=headers,
            params=params,
            timeout=30
        )
        response.raise_for_status()
        data = response.json()
        return data