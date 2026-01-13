import requests
from typing import Optional
from constants import *
from helpers.config import load_config
config = load_config()

def get_access_token() -> Optional[str]:
    """
    Obtiene el token de acceso para Microsoft Graph API
    """
    MICROSOFT_GRAPH_TENANT_ID=config['microsoft_graph']['tenant_id']
    MICROSOFT_GRAPH_CLIENT_ID=config['microsoft_graph']['client_id']
    MICROSOFT_GRAPH_CLIENT_SECRET=config['microsoft_graph']['client_secret']
    if not all([MICROSOFT_GRAPH_TENANT_ID, MICROSOFT_GRAPH_CLIENT_ID, MICROSOFT_GRAPH_CLIENT_SECRET]):
        print("Error: Microsoft Graph API credentials no configuradas en config.yaml")
        return None
    
    AUTHORITY = f"https://login.microsoftonline.com/{MICROSOFT_GRAPH_TENANT_ID}/oauth2/v2.0/token"
    try:
        response = requests.post(AUTHORITY, data={
            "grant_type": "client_credentials",
            "client_id": MICROSOFT_GRAPH_CLIENT_ID,
            "client_secret": MICROSOFT_GRAPH_CLIENT_SECRET,
            "scope": "https://graph.microsoft.com/.default"
        })
        
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get("access_token")
            
            if access_token:
                print("Token de acceso obtenido exitosamente")
                return access_token
            else:
                print("Error: No se pudo obtener el token de acceso")
                return None
        else:
            print(f"Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error al obtener el token: {e}")
        return None

def get_access_token_packing() -> Optional[str]:
    """
    Obtiene el token de acceso para Microsoft Graph API
    """
    if not all([MICROSOFT_GRAPH_TENANT_ID_PACKING, MICROSOFT_GRAPH_CLIENT_ID_PACKING, MICROSOFT_GRAPH_CLIENT_SECRET_PACKING]):
        print("Error: Microsoft Graph API credentials no configuradas en config.yaml")
        return None
    
    AUTHORITY = f"https://login.microsoftonline.com/{MICROSOFT_GRAPH_TENANT_ID}/oauth2/v2.0/token"
    try:
        response = requests.post(AUTHORITY, data={
            "grant_type": "client_credentials",
            "client_id": MICROSOFT_GRAPH_CLIENT_ID_PACKING,
            "client_secret": MICROSOFT_GRAPH_CLIENT_SECRET_PACKING,
            "scope": "https://graph.microsoft.com/.default"
        })
        
        if response.status_code == 200:
            token_response = response.json()
            access_token = token_response.get("access_token")
            
            if access_token:
                print("Token de acceso obtenido exitosamente")
                return access_token
            else:
                print("Error: No se pudo obtener el token de acceso")
                return None
        else:
            print(f"Error HTTP {response.status_code}: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error al obtener el token: {e}")
        return None

def get_config_value(section: str, key: str = None):
    """
    Obtiene un valor específico de la configuración
    
    Args:
        section: Sección del config (ej: 'microsoft_graph', 'onedrive', etc.)
        key: Clave específica dentro de la sección (opcional)
    
    Returns:
        El valor solicitado o None si no existe
    """
    # Importar config desde constants para acceso directo
    from constants import config
    
    if not config:
        print("Error: No se pudo cargar la configuración")
        return None
    
    if section not in config:
        print(f"Error: La sección '{section}' no existe en la configuración")
        return None
    
    if key is None:
        return config[section]
    
    if key not in config[section]:
        print(f"Error: La clave '{key}' no existe en la sección '{section}'")
        return None
    
    return config[section][key]

def print_config():
    """
    Imprime toda la configuración de manera organizada
    """
    # Importar config desde constants para acceso directo
    from constants import config
    
    if not config:
        print("Error: No se pudo cargar la configuración")
        return
    
    print("=== CONFIGURACIÓN CARGADA ===")
    for section, values in config.items():
        print(f"\n[{section.upper()}]")
        if isinstance(values, dict):
            for key, value in values.items():
                # Ocultar valores sensibles
                if 'secret' in key.lower() or 'token' in key.lower():
                    print(f"  {key}: ****")
                else:
                    print(f"  {key}: {value}")
        else:
            print(f"  {values}")