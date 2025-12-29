import yaml

# Cargar configuración desde config.yaml
with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

# Exportar config para otros módulos que lo necesiten

#CONEXION BD
#USER_BD = config['database']['user']
#PASS_BD = config['database']['password']
#SERVER_BD = config['database']['server']
#BD = config['database']['name']




#CONFIG APP
PORT = config['app']['port']
MODE_DEBUG = config['app']['debug']
NAME_EMPRESA = "Empresa"
NAME_USER = "Usuario"
LOGO = "logo.png"
RUBRO_EMPRESA = "Rubro"


PAGE_TITLE_PREFIX = "BI | "

# OneDrive/SharePoint Configuration
DRIVE_ID_CARPETA_STORAGE = "b!M5ucw3aa_UqBAcqv3a6affR7vTZM2a5ApFygaKCcATxyLdOhkHDiRKl9EvzaYbuR"
FOLDER_ID_CARPETA_STORAGE = "01XOBWFSBLVGULAQNEKNG2WR7CPRACEN7Q"

# Microsoft Graph API Configuration  
MICROSOFT_GRAPH_TENANT_ID = ""
MICROSOFT_GRAPH_CLIENT_ID = ""
MICROSOFT_GRAPH_CLIENT_SECRET = ""


#MICROSOFT_GRAPH_TENANT_ID_PACKING = config.get('microsoft_graph_packing', {}).get('tenant_id')
#MICROSOFT_GRAPH_CLIENT_ID_PACKING = config.get('microsoft_graph_packing', {}).get('client_id')
#MICROSOFT_GRAPH_CLIENT_SECRET_PACKING = config.get('microsoft_graph_packing', {}).get('client_secret')