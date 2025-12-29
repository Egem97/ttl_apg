import io
import base64
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT
import plotly.graph_objects as go
import plotly.io as pio
import pandas as pd
from reportlab.graphics.barcode import qr
from reportlab.graphics import renderPDF
from reportlab.graphics.shapes import Drawing

class DashboardPDFGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.setup_custom_styles()
        
    def setup_custom_styles(self):
        """Configurar estilos personalizados para el PDF"""
        # Título principal
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#094782')
        ))
        
        # Subtítulo
        self.styles.add(ParagraphStyle(
            name='CustomSubtitle',
            parent=self.styles['Heading2'],
            fontSize=16,
            spaceAfter=20,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#0b72d7')
        ))
        
        # Texto explicativo
        self.styles.add(ParagraphStyle(
            name='ExplanationText',
            parent=self.styles['Normal'],
            fontSize=11,
            spaceAfter=12,
            alignment=TA_JUSTIFY,
            leftIndent=0.2*inch
        ))
        
        # Texto de resumen
        self.styles.add(ParagraphStyle(
            name='SummaryText',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=8,
            alignment=TA_LEFT,
            textColor=colors.HexColor('#666666')
        ))

    def create_header(self, story):
        """Crear encabezado del reporte"""
        # Título principal
        title = Paragraph("📊 Reporte de Análisis Financiero", self.styles['CustomTitle'])
        story.append(title)
        
        # Subtítulo con fecha
        current_date = datetime.now().strftime("%d de %B de %Y")
        subtitle = Paragraph(f"Comparativo Presupuesto vs Ejecutado - {current_date}", self.styles['CustomSubtitle'])
        story.append(subtitle)
        
        story.append(Spacer(1, 20))

    def create_executive_summary(self, story, data_summary):
        """Crear resumen ejecutivo"""
        story.append(Paragraph("📋 Resumen Ejecutivo", self.styles['CustomSubtitle']))
        
        summary_text = f"""
        Este reporte presenta un análisis comparativo entre el presupuesto planificado y los gastos ejecutados 
        para el período seleccionado. Los datos incluyen información detallada por categorías de costos y 
        tendencias temporales que permiten identificar desviaciones y oportunidades de optimización.
        
        <b>Datos del período analizado:</b><br/>
        • Total Presupuestado: ${data_summary.get('total_presupuesto', 0):,.2f}<br/>
        • Total Ejecutado: ${data_summary.get('total_ejecutado', 0):,.2f}<br/>
        • Variación: {data_summary.get('variacion_porcentual', 0):.1f}%<br/>
        • Número de categorías analizadas: {data_summary.get('num_categorias', 0)}
        """
        
        story.append(Paragraph(summary_text, self.styles['ExplanationText']))
        story.append(Spacer(1, 20))

    def add_chart_to_pdf(self, story, fig, title, explanation):
        """Agregar gráfico con explicación al PDF"""
        # Título del gráfico
        story.append(Paragraph(title, self.styles['CustomSubtitle']))
        
        if fig is not None:
            try:
                # Convertir gráfico Plotly a imagen
                img_bytes = pio.to_image(fig, format="png", width=600, height=400, scale=2)
                img = Image(io.BytesIO(img_bytes), width=6*inch, height=4*inch)
                story.append(img)
            except Exception as e:
                print(f"Error convirtiendo gráfico a imagen: {e}")
                # Agregar mensaje de error en lugar del gráfico
                error_msg = Paragraph(
                    "<i>Error: No se pudo generar el gráfico para esta sección.</i>",
                    self.styles['SummaryText']
                )
                story.append(error_msg)
        else:
            # Agregar mensaje cuando no hay gráfico disponible
            no_chart_msg = Paragraph(
                "<i>Gráfico no disponible para esta sección.</i>",
                self.styles['SummaryText']
            )
            story.append(no_chart_msg)
        
        # Explicación del gráfico
        story.append(Paragraph("<b>Análisis:</b>", self.styles['Normal']))
        story.append(Paragraph(explanation, self.styles['ExplanationText']))
        story.append(Spacer(1, 20))

    def add_data_table(self, story, df, title, explanation):
        """Agregar tabla de datos al PDF"""
        story.append(Paragraph(title, self.styles['CustomSubtitle']))
        
        if df is not None and len(df) > 0:
            try:
                # Preparar datos para la tabla
                data = [df.columns.tolist()]  # Headers
                for _, row in df.iterrows():
                    data.append(row.tolist())
                
                # Crear tabla
                table = Table(data, repeatRows=1)
                table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#094782')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                    ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                
                story.append(table)
            except Exception as e:
                print(f"Error creando tabla: {e}")
                no_table_msg = Paragraph(
                    "<i>Error: No se pudo generar la tabla para esta sección.</i>",
                    self.styles['SummaryText']
                )
                story.append(no_table_msg)
        else:
            # Agregar mensaje cuando no hay datos disponibles
            no_data_msg = Paragraph(
                "<i>No hay datos disponibles para mostrar en esta tabla.</i>",
                self.styles['SummaryText']
            )
            story.append(no_data_msg)
        
        story.append(Paragraph(explanation, self.styles['ExplanationText']))
        story.append(Spacer(1, 20))

    def generate_dashboard_pdf(self, charts_data, tables_data, summary_data):
        """Generar PDF completo del dashboard"""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72,
                              topMargin=72, bottomMargin=18)
        
        story = []
        
        # Encabezado
        self.create_header(story)
        
        # Resumen ejecutivo
        self.create_executive_summary(story, summary_data)
        
        # Gráfico comparativo principal
        if 'main_chart' in charts_data:
            self.add_chart_to_pdf(
                story, 
                charts_data['main_chart'], 
                "📊 Gráfico Comparativo Principal",
                """Este gráfico muestra la comparación directa entre el presupuesto planificado y los gastos 
                ejecutados por categoría. Las barras azules representan el presupuesto asignado, mientras que 
                las barras azul claro muestran los gastos reales. Esta visualización permite identificar 
                rápidamente las categorías con mayor desviación presupuestaria y aquellas que se mantienen 
                dentro de los parámetros planificados."""
            )
        
        # Tabla de datos principales
        if 'main_table' in tables_data:
            main_table_df = None
            if tables_data['main_table']:
                try:
                    main_table_df = pd.DataFrame(tables_data['main_table'])
                except Exception as e:
                    print(f"Error creando DataFrame de tabla principal: {e}")
            
            self.add_data_table(
                story,
                main_table_df,
                "📋 Detalle por Categorías",
                """Esta tabla presenta el desglose detallado de cada categoría de costos, mostrando los montos 
                presupuestados versus los ejecutados. Los valores están formateados en dólares americanos y 
                permiten un análisis granular de cada línea presupuestaria."""
            )
        
        # Gráficos de predicción (si existen)
        prediction_charts = charts_data.get('prediction_charts', {})
        has_valid_predictions = any(chart for chart in prediction_charts.values() if chart is not None)
        
        if has_valid_predictions:
            story.append(PageBreak())
            story.append(Paragraph("🔮 Análisis Predictivo", self.styles['CustomSubtitle']))
            
            pred_explanation = """Los siguientes gráficos muestran las predicciones para las próximas 3 semanas 
            basadas en algoritmos de análisis de series temporales. Se utilizan tres metodologías diferentes:
            
            • <b>Media Móvil con Tendencia:</b> Utiliza promedios históricos ajustados por tendencia
            • <b>Suavizado Exponencial:</b> Pondera más los datos recientes para la predicción
            • <b>Regresión Lineal:</b> Identifica patrones lineales en los datos históricos
            
            Estas predicciones son herramientas de apoyo para la planificación y deben considerarse junto 
            con otros factores del negocio."""
            
            story.append(Paragraph(pred_explanation, self.styles['ExplanationText']))
            story.append(Spacer(1, 15))
            
            for chart_key, chart_fig in prediction_charts.items():
                variable_name = chart_key.replace('_', ' ').title()
                self.add_chart_to_pdf(
                    story,
                    chart_fig,  # Puede ser None, la función add_chart_to_pdf lo maneja
                    f"📈 Predicciones - {variable_name}",
                    f"""Este gráfico muestra las predicciones para {variable_name} utilizando los tres 
                    algoritmos mencionados. La línea sólida representa los datos históricos, mientras que 
                    las líneas punteadas muestran las proyecciones futuras. La convergencia o divergencia 
                    entre los algoritmos indica el nivel de certidumbre de las predicciones."""
                )
        else:
            # Agregar nota si no hay predicciones disponibles
            story.append(PageBreak())
            story.append(Paragraph("🔮 Análisis Predictivo", self.styles['CustomSubtitle']))
            no_predictions_msg = """No hay datos suficientes para generar predicciones en este período. 
            Las predicciones requieren datos históricos de KG_PROCESADOS y KG_EXPORTABLES con información 
            de semanas para poder aplicar los algoritmos de series temporales."""
            story.append(Paragraph(no_predictions_msg, self.styles['ExplanationText']))
            story.append(Spacer(1, 20))
        
        # Conclusiones y recomendaciones
        story.append(PageBreak())
        story.append(Paragraph("📝 Conclusiones y Recomendaciones", self.styles['CustomSubtitle']))
        
        conclusions = self.generate_conclusions(summary_data)
        story.append(Paragraph(conclusions, self.styles['ExplanationText']))
        
        # Footer
        story.append(Spacer(1, 30))
        footer_text = f"""
        <i>Reporte generado automáticamente el {datetime.now().strftime('%d/%m/%Y a las %H:%M')}.<br/>
        Sistema de Análisis Financiero - Versión 1.0</i>
        """
        story.append(Paragraph(footer_text, self.styles['SummaryText']))
        
        # Construir PDF
        doc.build(story)
        buffer.seek(0)
        return buffer

    def generate_conclusions(self, summary_data):
        """Generar conclusiones automáticas basadas en los datos"""
        total_ppto = summary_data.get('total_presupuesto', 0)
        total_ejec = summary_data.get('total_ejecutado', 0)
        variacion = summary_data.get('variacion_porcentual', 0)
        
        if variacion > 10:
            status = "sobreejecución significativa"
            recommendation = "Se recomienda revisar los procesos de control presupuestario y identificar las causas del exceso en el gasto."
        elif variacion > 5:
            status = "ligera sobreejecución"
            recommendation = "Monitorear de cerca las categorías con mayor desviación para evitar que la tendencia se mantenga."
        elif variacion < -10:
            status = "subejecución significativa"
            recommendation = "Evaluar si la subejecución responde a eficiencias operativas o a demoras en la implementación de proyectos."
        elif variacion < -5:
            status = "ligera subejecución"
            recommendation = "Verificar el progreso de los proyectos planificados y ajustar las proyecciones si es necesario."
        else:
            status = "ejecución dentro de parámetros normales"
            recommendation = "Mantener el nivel actual de control y seguimiento presupuestario."
        
        conclusions = f"""
        <b>Análisis General:</b><br/>
        El análisis del período muestra una {status} con una variación del {variacion:.1f}% 
        respecto al presupuesto planificado.
        
        <b>Recomendaciones:</b><br/>
        {recommendation}
        
        <b>Próximos Pasos:</b><br/>
        • Revisar mensualmente las categorías con mayor desviación<br/>
        • Actualizar las proyecciones basándose en las tendencias identificadas<br/>
        • Implementar alertas tempranas para desviaciones superiores al 15%<br/>
        • Considerar los factores estacionales en futuras planificaciones
        """
        
        return conclusions

def create_pdf_from_dashboard_data(filtered_data, charts, summary_data):
    """Función principal para crear PDF desde los datos del dashboard"""
    generator = DashboardPDFGenerator()
    
    # Preparar datos de gráficos
    charts_data = {
        'main_chart': charts.get('main_chart'),
        'prediction_charts': charts.get('prediction_charts', {})
    }
    
    # Preparar datos de tablas
    tables_data = {}
    if filtered_data and 'main_table_data' in filtered_data and filtered_data['main_table_data']:
        try:
            main_table_df = pd.DataFrame(filtered_data['main_table_data'])
            if len(main_table_df) > 0:
                tables_data['main_table'] = main_table_df
        except Exception as e:
            print(f"Error creando DataFrame para tabla principal: {e}")
            tables_data['main_table'] = pd.DataFrame()
    
    return generator.generate_dashboard_pdf(charts_data, tables_data, summary_data)

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape

class BoletaGenerator:
    def __init__(self, buffer):
        self.buffer = buffer
        self.page_width, self.page_height = A4 
        # Dimensiones lógicas de una boleta (diseño original horizontal)
        self.logical_width, self.logical_height = landscape(A4) 
        self.c = canvas.Canvas(self.buffer, pagesize=A4)

    def draw_header(self, data):
        c = self.c
        w = self.logical_width
        h = self.logical_height
        
        # Logo placeholder (Izquierda)
        try:
            # Logo un poco más grande y centrado en su espacio
            c.drawImage("assets/logo.jpg", 30, h - 95, width=80, height=60, mask='auto', preserveAspectRatio=True)
        except Exception as e:
            print(f"Error loading logo: {e}")
            
        # QR Code RUC
        try:
            qr_data = str(data.get('CORRELATIVO', '-'))
            qr_widget = qr.QrCodeWidget(qr_data)
            bounds = qr_widget.getBounds()
            width = bounds[2] - bounds[0]
            height = bounds[3] - bounds[1]
            
            # Desired size ~ 60x60
            size = 60.0
            scale = size / width
            
            d = Drawing(size, size, transform=[scale, 0, 0, scale, 0, 0])
            d.add(qr_widget)
            renderPDF.draw(d, c, 130, h - 95) # Posicionado a la derecha del logo
        except Exception as e:
            print(f"Error drawing QR: {e}")
        
        # Título Central
        c.setFont("Helvetica-Bold", 16)
        c.drawCentredString(w / 2, h - 50, "ALZA PERU PACKING S.A.C.")
        
        c.setFont("Helvetica", 7)
        c.drawCentredString(w / 2, h - 62, "OTR. SECTOR WICHANZAO VALLE MOCHE NRO. S/")
        c.drawCentredString(w / 2, h - 71, "N INT. 1 A.H. EL MILAGRO")
        c.drawCentredString(w / 2, h - 80, "LA LIBERTAD TRUJILLO - HUANCHACO")

        # Cuadro RUC (Derecha) - Estilo redondeado
        ruc_x = w - 250
        ruc_y = h - 100
        ruc_w = 220
        ruc_h = 75
        
        c.setLineWidth(1)
        c.setFillColor(colors.white) # Fondo blanco
        c.roundRect(ruc_x, ruc_y, ruc_w, ruc_h, 8, stroke=1, fill=0) # Contenedor principal
        
        # Líneas divisorias internas
        c.line(ruc_x, ruc_y + 50, ruc_x + ruc_w, ruc_y + 50)
        c.line(ruc_x, ruc_y + 25, ruc_x + ruc_w, ruc_y + 25)
        
        # Textos RUC
        c.setFillColor(colors.black)
        c.setFont("Helvetica-Bold", 12)
        c.drawCentredString(ruc_x + ruc_w/2, ruc_y + 58, "R.U.C. N° 20611417749")
        
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(colors.black) 
        c.drawCentredString(ruc_x + ruc_w/2, ruc_y + 33, "BOLETA DE DESPACHO")
        
        # Numero Boleta
        nro_boleta = str(data.get('CORRELATIVO', '-'))
        c.setFont("Helvetica-Bold", 14)
        c.setFillColor(colors.red)
        c.drawCentredString(ruc_x + ruc_w/2, ruc_y + 8, nro_boleta)
        c.setFillColor(colors.black)

    def draw_fields(self, data):
        c = self.c
        h = self.logical_height
        
        # --- Contenedor Izquierdo (Datos) ---
        left_box_x = 30
        left_box_y = h - 205
        left_box_w = 500
        left_box_h = 95
        
        c.setLineWidth(0.5)
        c.roundRect(left_box_x, left_box_y, left_box_w, left_box_h, 6, stroke=1, fill=0)
        
        start_y = left_box_y + left_box_h - 15
        line_step = 14
        font_size = 7
        
        fields = [
            ("DESTINATARIO:", data['DESTINATARIO']+" - "+data['FUNDO']),
            ("COMPRADOR:", "-"),
            ("PUNTO DE PARTIDA:", "VALLE MOCHE EL MILAGRO - TRUJILLO - LA LIBERTAD"),
            ("PUNTO DE LLEGADA:", data.get('PUNTO DE LLEGADA', '')+" - "+data['FUNDO']),
            ("PREPARADOR POR:", data.get('USUARIO', '')),
        ]
        current_y = start_y
        # Fecha de Inicio de Traslado (Line with boxes)
        c.setFont("Helvetica-Bold", 11)
        c.drawString(left_box_x + 10, current_y, "FECHA:")
        
        # Boxes for date [ ] [ ] [ ]
        # c.setFont("Helvetica-Bold", 11) # Ya establecido arriba
        fecha_str = str(data.get('FECHA', ''))
        c.drawString(left_box_x + 100, current_y, fecha_str) 
        
        #c.line(left_box_x + 50, current_y - 2, left_box_x + 155, current_y - 2)
        
        # Mover una fila abajo para los siguientes campos
        current_y -= line_step

        c.setFont("Helvetica", font_size)
        
        for i, (label, value) in enumerate(fields):
            # Etiqueta
            c.drawString(left_box_x + 10, current_y, label)
            
            # Linea y Valor
            line_start_x = left_box_x + 100
            line_end_x = left_box_x + 330
            c.line(line_start_x, current_y - 2, line_end_x, current_y - 2)
            c.drawString(line_start_x + 2, current_y, str(value if value else ''))

            # Campos RUC adicionales en las dos primeras lineas
            if i == 0 or i == 1:
                ruc_label = "N° DE RUC:"
                c.drawString(left_box_x + 340, current_y, ruc_label)
                c.line(left_box_x + 385, current_y - 2, left_box_x + 490, current_y - 2)
                
                if i == 0:
                    ruc_val = str(data.get('Nº RUC DESTINATARIO', ''))
                else:
                    ruc_val = "-"
                    
                c.drawString(left_box_x + 390, current_y, ruc_val)
                
            current_y -= line_step

        

        
        # --- Contenedor Derecho (Checkboxes de Operación) ---
        right_box_x = 540
        right_box_y = h - 205
        right_box_w = 270
        right_box_h = 95
        
        c.roundRect(right_box_x, right_box_y, right_box_w, right_box_h, 6, stroke=1, fill=0)
        
        # Opciones
        col1_x = right_box_x + 10
        col2_x = right_box_x + 140
        opts_y_start = right_box_y + right_box_h - 15
        
        col1_opts = ["VENTA", "VENTA SUJETA A CONFIRMACIÓN", "COMPRA", "CONSIGNACIÓN", "IMPORTACIÓN", "OTROS"]
        col2_opts = ["MATERIALES", "EXPORTACIÓN", "TRASLADO DE BIENES", "PARA TRANSFORMACIÓN", "ENTRE ESTABLECIMIENTO DE", "LA MISMA EMPRESA"]
        
        # Checkbox drawing helper
        def draw_check_item(x, y, text, checked=False):
            c.rect(x, y, 6, 6, fill=1 if checked else 0)
            c.drawString(x + 10, y, text)
            
        c.setFont("Helvetica", 6)
        
        # Col 1
        curr_y = opts_y_start
        for opt in col1_opts:
            draw_check_item(col1_x, curr_y, opt)
            curr_y -= 12
            
        # Col 2
        curr_y = opts_y_start
        # Special case for multi-line items in col 2 or just list distinct
        # Logic adjustment for "TRASLADO ... PARA TRANSFORMACION" looks like 2 lines visually in image
        # But we list flat for simplicity unless specific
        
        draw_check_item(col2_x, opts_y_start, "MATERIALES", checked=True)
        draw_check_item(col2_x, opts_y_start - 12, "EXPORTACIÓN")
        
        # Multi line simulation
        draw_check_item(col2_x, opts_y_start - 24, "TRASLADO DE BIENES")
        c.drawString(col2_x + 10, opts_y_start - 32, "PARA TRANSFORMACIÓN")
        
        draw_check_item(col2_x, opts_y_start - 48, "ENTRE ESTABLECIMIENTO DE")
        c.drawString(col2_x + 10, opts_y_start - 56, "LA MISMA EMPRESA")

    def draw_table_header(self, y_pos):
        c = self.c
        headers = ["CODIGO", "CANTIDAD", "UNID", "DESCRIPCION", "PESO BRUTO", "PESO NETO", "OBSERVACIÓN"]
        widths = [80, 80, 60, 250, 80, 80, 150]
        x = 40
        
        c.setFillColor(colors.grey)
        c.rect(30, y_pos - 15, sum(widths), 20, fill=1)
        c.setFillColor(colors.white)
        c.setFont("Helvetica-Bold", 9)
        
        current_x = 30
        for h, w in zip(headers, widths):
            c.drawCentredString(current_x + w/2, y_pos - 10, h)
            current_x += w
        c.setFillColor(colors.black)
        return current_x # Total width

    def draw_table_row(self, y_pos, data):
        c = self.c
        widths = [80, 80, 60, 250, 80, 80, 150]
        row_height = 20
        
        # Lista de columnas de materiales a procesar (según estructura de datos)
        # Se verifica si existen y si tienen cantidad > 0
        materials = [
            "JABAS VACIAS",
            "JARRAS VACIAS",
            "PARIHUELAS",
            "ESQUINEROS",
            "JABAS CON DESCARTE",
            "JARRAS CON DESCARTE",

        ]
        
        c.setFont("Helvetica", 9)
        current_y = y_pos
        has_items = False
        
        # Lista de items validos
        valid_rows = []
        for material in materials:
            print(material)
            try:
                val = data.get(material, 0)
                print(val)
                if pd.isna(val) or val == '': val = 0
                qty = float(val)
                
                if qty > 0:
                    qty_str = str(int(qty)) if qty.is_integer() else f"{qty:.2f}"
                    valid_rows.append([
                        "-",                    # N° PRECINTO
                        qty_str,                # CANTIDAD
                        "UND",                  # UNIDAD
                        material,               # DESCRIPCION
                        "-",                    # PESO BRUTO
                        "-",                    # PESO NETO
                        data.get('OBSERVACIONES', ''), # OBSERVACION
                    ])
                    #data.get('Nº PRECINTO', '')
            except Exception:
                continue

        # Lógica para Precintos
        precinto_val = data.get('Nº PRECINTO', '')
        if precinto_val and str(precinto_val).strip() not in ['', '-', 'nan', 'None']:
            try:
                precinto_str = str(precinto_val)
                # Contar precintos separados por guion
                qty_precintos = len([p for p in precinto_str.split('-') if p.strip()])
                
                valid_rows.append([
                    precinto_str,               # CODIGO
                    str(qty_precintos),         # CANTIDAD
                    "UND",                      # UNID
                    "PRECINTOS",                # DESCRIPCION
                    "-",                        # PESO BRUTO
                    "-",                        # PESO NETO
                    data.get('OBSERVACIONES') or '' # OBSERVACION
                ])
            except Exception as e:
                print(f"Error processing precintos: {e}")
                
        # Dibujar siempre 5 filas
        num_rows = 5
        c.setFont("Helvetica", 8)
        
        for i in range(num_rows):
            if i < len(valid_rows):
                row_data = valid_rows[i]
            else:
                # Fila vacía para completar formato
                row_data = ["-", "", "", "", "-", "-", ""]
            
            # Dibujar celdas (menos la última columna)
            current_x = 30
            for j, (val, w) in enumerate(zip(row_data, widths)):
                if j == len(widths) - 1: # Saltar columna Observación
                    continue
                    
                c.drawCentredString(current_x + w/2, current_y - 14, str(val)) 
                c.rect(current_x, current_y - 20, w, 20)
                current_x += w
            
            current_y -= row_height

        # Dibujar celda fusionada de Observación
        obs_idx = len(widths) - 1
        obs_w = widths[obs_idx]
        obs_x = 30 + sum(widths[:obs_idx])
        total_h = num_rows * row_height
        
        # El current_y ahora está en la base de la tabla tras el loop
        # Dibujamos el rectangulo desde ahí hacia arriba
        c.rect(obs_x, current_y, obs_w, total_h)
        c.drawCentredString(obs_x + obs_w/2, current_y + total_h/2 - 4, data.get('OBSERVACIONES') or 'DEVOLUCIÓN DE MATERIAL')

    def draw_single_boleta(self, data):
        c = self.c
        w = self.logical_width
        h = self.logical_height

        # --- Contorno General ---
        c.setLineWidth(1.5)
        # Coordenadas aproximadas cubriendo desde Header hasta bajo la firma
        # Margin reduced to 12 for wider box
        c.rect(12, 130, w - 24, h - 150)
        c.setLineWidth(1) # Resetear para el resto

        self.draw_header(data)
        self.draw_fields(data)
        
        # Tabla - Movida hacia arriba para reducir espacio en blanco
        h = self.logical_height
        # Los boxes de fields terminan en y = h - 205.
        # Dejamos un margen pequeño (ej. 15 pt), entonces header de tabla en h - 220.
        y_table = h - 220 
        
        self.draw_table_header(y_table)
        
        # Dibujar filas de materiales
        self.draw_table_row(y_table - 20, data)
        
        # Footer
        c = self.c
        # Footer también sube. 
        # Si la tabla tiene 1 fila, termina en y_table - 40.
        # Pongamos el footer base en y = 140 para que quede pegado pero con aire.
        # Check if we didn't invoke too many rows overlap. (Max 6 rows = 120pts used)
        # y_table (375) - 20 (header) - 120 (rows) = 235. Footer at 140. PLENTY of space.
        y_footer_base = 140
        
        # Reset color/font for footer
        c.setFillColor(colors.black)
        
        # Titulo seccion inferior
        c.setFont("Helvetica-Bold", 7)
        c.drawString(40, y_footer_base + 65, "HECHO POR APG PACKING") 
        
        c.setFont("Helvetica", 6)
        
        # Ajustamos coordenadas para dar espacio al recuadro de firma (Width ~120 reserved at right)
        # Max width ~840. Box starts ~700. Lines should end ~690.
        
        # Linea 1: Apellidos y Nombres Transportista
        y_row1 = y_footer_base + 50
        c.drawString(40, y_row1, "APELLIDOS Y NOMBRES Ó RAZÓN SOCIAL DEL TRANSPORTISTAS:")
        c.line(260, y_row1 - 2, 690, y_row1 - 2)
        c.drawString(265, y_row1, str(data.get('RAZON SOCIAL TRANSPORTE', ''))) 

        # Linea 2: Domicilio, RUC, Marca
        # Redistribuimos para ganar espacio
        y_row2 = y_footer_base + 35
        
        # Col 1
        c.drawString(40, y_row2, "DOMICILIO FISCAL:")
        c.line(110, y_row2 - 2, 280, y_row2 - 2)
        c.drawString(115, y_row2, "-")
        # Col 2
        c.drawString(290, y_row2, "N° DE RUC:")
        c.line(330, y_row2 - 2, 450, y_row2 - 2) # Reduced end from 480
        c.drawString(335, y_row2, str(data.get('Nº RUC TRANSPORTISTA', '')))
        
        # Col 3
        c.drawString(460, y_row2, "MARCA DEL VEHICULO:") # Moved left from 490
        c.line(540, y_row2 - 2, 690, y_row2 - 2) # Start 540 (was 570), End 690 (was 700)
        c.drawString(545, y_row2, str(data.get('MARCA_VEHICULO', '-')))

        # Linea 3: Placa, Chofer, Constancia
        y_row3 = y_footer_base + 20
        
        # Col 1
        c.drawString(40, y_row3, "PLACA VEHICULO:")
        c.line(105, y_row3 - 2, 180, y_row3 - 2)
        c.drawString(110, y_row3, str(data.get('PLACA', data.get('Nº PLACA', ''))))
        
        # Col 2
        c.drawString(200, y_row3, "NOMBRE DEL CHOFER:") # Moved slightly
        c.line(280, y_row3 - 2, 450, y_row3 - 2) # End 450
        c.drawString(285, y_row3, str(data.get('CONDUCTOR', '-')))
        
        # Col 3
        c.drawString(460, y_row3, "N° DE CONSTANCIA DE RECEPCIÓN:") # Moved left from 490
        c.line(585, y_row3 - 2, 690, y_row3 - 2) # Start 585 (was 615), End 690
        c.drawString(590, y_row3, "-")
        # Constancia signature box (Derecha)
        # Hacemos el cuadro mas ancho y acomodamos el texto
        box_x = 700
        box_w = 110
        center_x = box_x + box_w / 2
        
        c.roundRect(box_x, y_footer_base + 15, box_w, 50, 4, stroke=1, fill=0)
        
        c.setFont("Helvetica", 4)
        # Separamos en lineas para que entre bien
        c.drawCentredString(center_x, y_footer_base + 23, "FIRMA Y SELLO DE CLIENTE O TRANSPORTISTA")
        c.drawCentredString(center_x, y_footer_base + 18, "EN SEÑAL DE HABER RECIBIDO CONFORME")

    def generate(self, data_list):
        for i, data in enumerate(data_list):
            if i > 0 and i % 2 == 0:
                self.c.showPage()
            
            self.c.saveState()
            
            scale = 0.7
            # Margen izquierdo para centrar (Ancho A4 - Ancho Boleta Escalado) / 2
            margin_x = (self.page_width - (self.logical_width * scale)) / 2
            
            if i % 2 == 0:
                # Boleta Superior
                # Posicionar en la mitad superior de A4
                # Translación Y: Empezar un poco debajo del borde superior
                self.c.translate(margin_x, self.page_height * 0.48) 
            else:
                # Boleta Inferior
                # Posicionar en la mitad inferior
                self.c.translate(margin_x, 20)
                
            self.c.scale(scale, scale)
            self.draw_single_boleta(data)
            self.c.restoreState()
            
        self.c.save()
        self.buffer.seek(0)
        return self.buffer

def generate_boleta_pdf(data_list):
    buffer = io.BytesIO()
    # Asegúrate de pasar data_list como lista de dicts
    generator = BoletaGenerator(buffer)
    return generator.generate(data_list)