import yaml
import os
# Cargar configuración desde YAML
def load_config():
    """
    Carga la configuración desde el archivo config.yaml
    """
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.yaml')
    
    try:
        with open(config_path, 'r', encoding='utf-8') as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: No se encontró el archivo de configuración en {config_path}")
        return None
    except yaml.YAMLError as e:
        print(f"Error al leer el archivo YAML: {e}")
        return None