"""
Ejemplo de nueva página creada con la arquitectura escalable
Demuestra cómo crear un dashboard completamente diferente en minutos
"""
import dash
import dash_mantine_components as dmc
from constants import PAGE_TITLE_PREFIX
from core.dashboard_factory import dashboard_factory, DashboardConfig
from config.dashboard_configs import VENTAS_CONFIG

dash.register_page(__name__, "/ventas", title=PAGE_TITLE_PREFIX + "Ventas")
dmc.add_figure_templates(default="mantine_light")

# Crear dashboard de ventas usando configuración declarativa
config = DashboardConfig(VENTAS_CONFIG)
layout = dashboard_factory.create_dashboard(config)

# ¡Solo 3 líneas de código para un dashboard completo!
# La configuración está en config/dashboard_configs.py
# Los datos se manejan automáticamente por el DataManager