import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from utilidades.estados_revision import (
    describir_estado_revision,
    nivel_de_puntaje,
    titulo_informe,
)

def generar_dossier_pdf_auditoria(datos_caso: dict, df_explicacion, ruta_salida: str = None) -> str:
    """
    Genera un archivo PDF estructurado (Dossier de Evidencia de Auditoría) con ReportLab.
    """
    if not ruta_salida:
        os.makedirs("./reportes_pdf", exist_ok=True)
        ruta_salida = f"./reportes_pdf/Dossier_Auditoria_Conv_{datos_caso.get('id_convocatoria', 0)}.pdf"

    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=letter,
        rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Estilos personalizados
    titulo_style = ParagraphStyle(
        'TituloDossier',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=16,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=6
    )

    subtitulo_style = ParagraphStyle(
        'SubtituloDossier',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        textColor=colors.HexColor('#1E88E5'),
        spaceBefore=10,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'BodyDossier',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#334155')
    )

    elements = []

    # Encabezado
    elements.append(Paragraph("DOSSIER OFICIAL DE EVIDENCIA DE AUDITORÍA DE FRACCIONAMIENTO", titulo_style))
    elements.append(Paragraph("Sistema de Inteligencia Artificial de Detección Preventiva - SEACE / OSCE", body_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#1E88E5'), spaceAfter=12))

    # El puntaje se persiste en una escala de 0 a 100. El color sigue el nivel
    # de riesgo; el texto, el estado de revisión, para no presentar una
    # propuesta del sistema como conclusión.
    score = float(datos_caso.get('puntaje_riesgo', 0.0))
    con_auditor = datos_caso.get('id_usuario_auditor') is not None
    badge_color = colors.HexColor(
        {'Alto': '#FF4D4D', 'Medio': '#FFA500', 'Bajo': '#2ECC71'}[nivel_de_puntaje(score)]
    )
    badge_text = titulo_informe(
        datos_caso.get('estado_revision'), con_auditor, score
    ).upper()

    data_badge = [[Paragraph(f"<font color='white'><b>{badge_text} ({score:.1f} PUNTOS)</b></font>", body_style)]]
    t_badge = Table(data_badge, colWidths=[540])
    t_badge.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), badge_color),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
    ]))
    elements.append(t_badge)
    elements.append(Spacer(1, 12))

    # Resumen de Convocatoria
    elements.append(Paragraph("1. Información General de la Convocatoria", subtitulo_style))
    tabla_info = [
        [Paragraph("<b>ID Convocatoria:</b>", body_style), Paragraph(str(datos_caso.get('id_convocatoria')), body_style),
         Paragraph("<b>Fecha Registro:</b>", body_style), Paragraph(str(datos_caso.get('fecha_convocatoria')), body_style)],
        [Paragraph("<b>RUC Entidad:</b>", body_style), Paragraph(str(datos_caso.get('entidad_ruc')), body_style),
         Paragraph("<b>Monto Referencial:</b>", body_style), Paragraph(f"S/ {float(datos_caso.get('monto_referencial', 0)):,.2f}", body_style)],
        [Paragraph("<b>Entidad Publica:</b>", body_style), Paragraph(str(datos_caso.get('entidad_nombre')), body_style),
         Paragraph("<b>Código CUBSO:</b>", body_style), Paragraph(str(datos_caso.get('codigo_cubso', 'GENERAL')), body_style)],
    ]
    t_info = Table(tabla_info, colWidths=[110, 160, 110, 160])
    t_info.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#F8F9FA')),
        ('BACKGROUND', (2,0), (2,-1), colors.HexColor('#F8F9FA')),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_info)
    elements.append(Spacer(1, 10))

    # Descripción del Objeto
    elements.append(Paragraph("<b>Descripción Completa del Objeto de Contratación:</b>", body_style))
    elements.append(Paragraph(f"<i>\"{datos_caso.get('descripcion_item', '')}\"</i>", body_style))
    elements.append(Spacer(1, 12))

    # Explicabilidad XAI
    elements.append(Paragraph("2. Fundamentos del puntaje (factores de impacto)", subtitulo_style))
    
    tabla_xai = [[Paragraph("<b>Variable Analizada</b>", body_style), 
                  Paragraph("<b>Valor Observado</b>", body_style), 
                  Paragraph("<b>Contribución al Riesgo (%)</b>", body_style)]]
    
    if not df_explicacion.empty:
        for _, r in df_explicacion.iterrows():
            tabla_xai.append([
                Paragraph(str(r['variable_nombre']), body_style),
                Paragraph(str(r['valor_observado']), body_style),
                Paragraph(f"<b>{float(r['impacto_porcentaje']):.2f}%</b>", body_style)
            ])

    t_xai = Table(tabla_xai, colWidths=[240, 150, 150])
    t_xai.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E2E8F0')),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 5),
    ]))
    elements.append(t_xai)
    elements.append(Spacer(1, 14))

    # Dictamen Human-in-the-Loop
    elements.append(Paragraph("3. Dictamen y Validación del Auditor (Human-in-the-Loop)", subtitulo_style))
    # Misma descripción que el Centro de control: sin auditor registrado no
    # se presenta como dictamen.
    etiqueta_estado, detalle_estado = describir_estado_revision(
        datos_caso.get('estado_revision'),
        con_auditor,
    )
    estado = f"{etiqueta_estado} ({detalle_estado.lower()})"
    comentario = str(datos_caso.get('comentario_auditor') or '').strip() or 'Sin comentarios'

    tabla_aud = [
        [Paragraph("<b>Estado de Revisión:</b>", body_style), Paragraph(f"<b>{estado}</b>", body_style)],
        [Paragraph("<b>Comentarios de Auditoría:</b>", body_style), Paragraph(str(comentario), body_style)]
    ]
    t_aud = Table(tabla_aud, colWidths=[140, 400])
    t_aud.setStyle(TableStyle([
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
        ('PADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(t_aud)
    elements.append(Spacer(1, 30))

    # Bloque de Firma
    tabla_firma = [
        [Paragraph("________________________________________", body_style), Paragraph("________________________________________", body_style)],
        [Paragraph("<b>Firma del Auditor Responsable</b>", body_style), Paragraph("<b>Sello de Contraloría / Auditoría Interna</b>", body_style)]
    ]
    t_firma = Table(tabla_firma, colWidths=[270, 270])
    t_firma.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
    ]))
    elements.append(t_firma)

    doc.build(elements)
    return ruta_salida
