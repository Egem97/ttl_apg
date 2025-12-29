"""
Dashboard con Filtros Dependientes - Implementación Manual
Ejemplo de cómo implementar los filtros usando tu estructura original
"""
import asyncio
import dash
import dash_mantine_components as dmc
from dash import html, dcc, callback, Input, Output, State
from components.grid import Row, Column
from components.simple_components import create_page_header
from constants import PAGE_TITLE_PREFIX
from helpers.helpers import generate_list_month

dash.register_page(__name__, "/costos-manual", title=PAGE_TITLE_PREFIX + "Costos Manual")

# ============================================================
# CONFIGURACIÓN
# ============================================================

PAGE_ID = "costos-manual-"
DATA_SOURCE = "costos_diarios"
START_YEAR = 2024
START_MONTH = 1

# ============================================================
# LAYOUT MANUAL (tu estilo original)
# ============================================================

def create_custom_layout():
    return html.Div([
        # Store para datos de fechas
        dcc.Store(id=f"{PAGE_ID}dates-store"),
        
        # Header personalizado
        dmc.Container([
            Row([
                Column([
                    create_page_header(
                        title="💰 Costos Diarios Manual",
                        subtitle="Implementación manual de filtros dependientes"
                    )
                ], size=5),
                
                Column([
                    dmc.Select(
                        id=f"{PAGE_ID}year",
                        label="Año",
                        placeholder="Seleccione Año",
                        clearable=False,
                        data=[],
                        mb="md"
                    )
                ], size=1),
                
                Column([
                    dmc.Select(
                        id=f"{PAGE_ID}month",
                        label="Mes", 
                        placeholder="Seleccione Mes",
                        clearable=True,
                        data=[],
                        mb="md"
                    )
                ], size=2),
                
                Column([
                    dmc.MultiSelect(
                        id=f"{PAGE_ID}week",
                        label="Semana",
                        placeholder="Seleccione Semana",
                        clearable=True,
                        data=[],
                        mb="md"
                    )
                ], size=4)
            ])
        ], size="xl", mb="md"),
        
        # Área para mostrar selecciones actuales
        dmc.Container([
            dmc.Card([
                dmc.Text("🔍 Filtros Seleccionados:", fw=500, mb="sm"),
                html.Div(id=f"{PAGE_ID}current-filters", children="Sin filtros seleccionados")
            ], p="md", withBorder=True)
        ], size="xl")
    ])

layout = create_custom_layout()

# ============================================================
# CALLBACKS MANUALES
# ============================================================

# 1. Callback para cargar datos iniciales usando generate_list_month
@callback(
    Output(f"{PAGE_ID}dates-store", "data"),
    Input(f"{PAGE_ID}year", "id"),  # Trigger inicial
    prevent_initial_call=False
)
async def load_dates_data(_):
    """Carga datos de fechas usando generate_list_month"""
    try:
        print(f"🗓️ Generando datos desde {START_YEAR}/{START_MONTH}")
        
        # Llamar generate_list_month de forma asíncrona
        df_dates = await asyncio.to_thread(generate_list_month, START_YEAR, START_MONTH)
        
        if df_dates is not None and not df_dates.empty:
            print(f"✅ Datos de fechas generados: {len(df_dates)} registros")
            return df_dates.to_dict('records')
        return []
        
    except Exception as e:
        print(f"❌ Error generando datos: {e}")
        return []

# 2. Callback para opciones de año
@callback(
    Output(f"{PAGE_ID}year", "data"),
    Input(f"{PAGE_ID}dates-store", "data"),
    prevent_initial_call=False
)
async def update_year_options(dates_data):
    """Actualiza opciones de año"""
    if not dates_data:
        return []
    
    try:
        # Extraer años únicos
        years = list(set([record['YEAR'] for record in dates_data]))
        years.sort(reverse=True)  # Más recientes primero
        
        return [{'label': str(year), 'value': str(year)} for year in years]
        
    except Exception as e:
        print(f"❌ Error actualizando años: {e}")
        return []

# 3. Callback para opciones de mes (dependiente del año)
@callback(
    Output(f"{PAGE_ID}month", "data"),
    Input(f"{PAGE_ID}year", "value"),
    State(f"{PAGE_ID}dates-store", "data"),
    prevent_initial_call=False
)
async def update_month_options(selected_year, dates_data):
    """Actualiza opciones de mes basado en el año seleccionado"""
    if not dates_data or selected_year is None:
        return []
    
    try:
        # Filtrar meses para el año seleccionado
        months_for_year = [
            record for record in dates_data 
            if record['YEAR'] == selected_year
        ]
        
        # Crear diccionario para evitar duplicados
        month_dict = {}
        for record in months_for_year:
            month_num = record['MES']
            month_text = record['MES_TEXT']
            month_dict[month_num] = month_text
        
        # Ordenar por número de mes
        sorted_months = sorted(month_dict.items())
        
        return [
            {'label': month_text, 'value': str(month_num)}
            for month_num, month_text in sorted_months
        ]
        
    except Exception as e:
        print(f"❌ Error actualizando meses: {e}")
        return []

# 4. Callback para opciones de semana (dependiente del año y mes)
@callback(
    Output(f"{PAGE_ID}week", "data"),
    [Input(f"{PAGE_ID}year", "value"), Input(f"{PAGE_ID}month", "value")],
    State(f"{PAGE_ID}dates-store", "data"),
    prevent_initial_call=False
)
async def update_week_options(selected_year, selected_month, dates_data):
    """Actualiza opciones de semana basado en año y mes seleccionados"""
    if not dates_data or selected_year is None:
        return []
    
    try:
        # Filtrar por año
        filtered_data = [
            record for record in dates_data 
            if record['YEAR'] == selected_year
        ]
        
        # Si hay mes seleccionado, filtrar también por mes
        if selected_month is not None:
            filtered_data = [
                record for record in filtered_data
                if record['MES'] == selected_month
            ]
        
        # Extraer semanas únicas
        weeks = list(set([record['SEMANA'] for record in filtered_data]))
        weeks.sort()
        
        return [
            {'label': f'Semana {week}', 'value': str(week)}
            for week in weeks
        ]
        
    except Exception as e:
        print(f"❌ Error actualizando semanas: {e}")
        return []

# 5. Callback para mostrar filtros actuales
@callback(
    Output(f"{PAGE_ID}current-filters", "children"),
    [Input(f"{PAGE_ID}year", "value"), 
     Input(f"{PAGE_ID}month", "value"), 
     Input(f"{PAGE_ID}week", "value")]
)
def show_current_filters(year, month, weeks):
    """Muestra los filtros seleccionados actualmente"""
    
    if not year:
        return "Sin filtros seleccionados"
    
    filters = [f"Año: {year} (tipo: {type(year).__name__})"]
    
    if month:
        filters.append(f"Mes: {month} (tipo: {type(month).__name__})")
    
    if weeks:
        if isinstance(weeks, list):
            weeks_str = ", ".join([f"Sem {w}" for w in weeks])
            filters.append(f"Semanas: {weeks_str} (tipo: lista)")
        else:
            weeks_str = f"Sem {weeks}"
            filters.append(f"Semanas: {weeks_str} (tipo: {type(weeks).__name__})")
    
    # Mostrar información técnica
    info_parts = [" | ".join(filters)]
    
    if year or month or weeks:
        info_parts.append("📝 Nota: Los valores ahora son strings (requerido por Mantine)")
        
        # Mostrar cómo se convertirían para filtrar datos
        conversions = []
        if year:
            try:
                year_int = int(year)
                conversions.append(f"Año para filtrar: {year_int}")
            except (ValueError, TypeError):
                conversions.append(f"Año (error conversión): {year}")
        
        if month:
            try:
                month_int = int(month)
                conversions.append(f"Mes para filtrar: {month_int}")
            except (ValueError, TypeError):
                conversions.append(f"Mes (error conversión): {month}")
                
        if weeks:
            try:
                if isinstance(weeks, list):
                    weeks_int = [int(w) for w in weeks]
                    conversions.append(f"Semanas para filtrar: {weeks_int}")
                else:
                    week_int = int(weeks)
                    conversions.append(f"Semana para filtrar: {week_int}")
            except (ValueError, TypeError):
                conversions.append(f"Semanas (error conversión): {weeks}")
        
        if conversions:
            info_parts.append("🔄 Conversiones: " + " | ".join(conversions))
    
    return html.Div([
        html.P(info_parts[0]),
        *[html.P(part, style={"fontSize": "12px", "color": "gray"}) for part in info_parts[1:]]
    ])