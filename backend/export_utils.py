"""
Export utilities for generating PDF and XLSX reports
"""
from datetime import datetime
from typing import List, Dict, Any
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter


def format_currency(value: float, locale: str = 'en') -> str:
    """Format currency value"""
    if locale == 'it':
        return f"€{value:,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    return f"€{value:,.2f}"


def generate_daily_prep_pdf(
    data: List[Dict[str, Any]],
    date: str,
    restaurant_name: str,
    locale: str = 'en'
) -> bytes:
    """Generate Daily Preparations PDF export"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.75*inch)
    
    # Container for elements
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor('#059669'),
        spaceAfter=12,
        alignment=TA_CENTER
    )
    
    # Header
    title_text = "Daily Preparations" if locale == 'en' else "Preparazioni Giornaliere"
    title = Paragraph(f"<b>{restaurant_name}</b><br/>{title_text}", title_style)
    elements.append(title)
    
    date_text = f"Date: {date}" if locale == 'en' else f"Data: {date}"
    date_para = Paragraph(date_text, styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.3*inch))
    
    # Table data
    if locale == 'en':
        table_data = [['Preparation', 'Planned', 'To Prepare', 'Unit', 'Shelf Life', 'Cost/Portion', 'Total Cost', 'Notes']]
    else:
        table_data = [['Preparazione', 'Pianif.', 'Da Prep.', 'Unità', 'Scadenza', 'Costo/Porz.', 'Costo Tot.', 'Note']]
    
    total_cost = 0
    total_portions = 0
    
    for item in data:
        shelf_life = item.get('shelfLife', '-')
        cost_per_portion = item.get('costPerPortion', 0)
        total_item_cost = item.get('totalCost', 0)
        notes = item.get('notes', '-')
        
        table_data.append([
            item.get('name', ''),
            str(item.get('plannedPortions', 0)),
            str(item.get('toPrepare', 0)),
            item.get('unit', 'portions'),
            shelf_life,
            format_currency(cost_per_portion, locale),
            format_currency(total_item_cost, locale),
            notes[:20] + '...' if len(notes) > 20 else notes
        ])
        
        total_cost += total_item_cost
        total_portions += item.get('toPrepare', 0)
    
    # Totals row
    totals_label = 'TOTALS' if locale == 'en' else 'TOTALI'
    table_data.append(['', '', str(total_portions), '', '', '', format_currency(total_cost, locale), ''])
    
    # Create table
    table = Table(table_data, colWidths=[1.8*inch, 0.7*inch, 0.7*inch, 0.7*inch, 0.8*inch, 0.9*inch, 0.9*inch, 1.2*inch])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#059669')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('ALIGN', (1, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#f0fdf4')),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('ROWBACKGROUNDS', (0, 1), (-1, -2), [colors.white, colors.HexColor('#f9fafb')])
    ]))
    
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 0.3*inch))
    footer_text = f"Exported: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    footer = Paragraph(footer_text, styles['Italic'])
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    
    return buffer.getvalue()


def generate_daily_prep_xlsx(
    data: List[Dict[str, Any]],
    date: str,
    restaurant_name: str,
    locale: str = 'en'
) -> bytes:
    """Generate Daily Preparations XLSX export"""
    wb = Workbook()
    ws = wb.active
    ws.title = f"DailyPreparations_{date}"
    
    # Styles
    header_font = Font(bold=True, color="FFFFFF", size=11)
    header_fill = PatternFill(start_color="059669", end_color="059669", fill_type="solid")
    total_fill = PatternFill(start_color="f0fdf4", end_color="f0fdf4", fill_type="solid")
    border = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    # Title and date
    ws.merge_cells('A1:H1')
    ws['A1'] = f"{restaurant_name} - Daily Preparations"
    ws['A1'].font = Font(bold=True, size=14)
    ws['A1'].alignment = Alignment(horizontal='center')
    
    ws['A2'] = f"Date: {date}"
    ws['A2'].font = Font(bold=True)
    
    # Headers
    if locale == 'en':
        headers = ['Preparation', 'Planned Portions', 'To Prepare', 'Unit', 'Shelf Life', 'Cost/Portion', 'Total Cost', 'Notes']
    else:
        headers = ['Preparazione', 'Porzioni Pianif.', 'Da Preparare', 'Unità', 'Scadenza', 'Costo/Porzione', 'Costo Totale', 'Note']
    
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=header)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal='center', vertical='center')
        cell.border = border
    
    # Data rows
    total_cost = 0
    total_portions = 0
    
    for idx, item in enumerate(data, 5):
        ws.cell(row=idx, column=1, value=item.get('name', ''))
        ws.cell(row=idx, column=2, value=item.get('plannedPortions', 0))
        ws.cell(row=idx, column=3, value=item.get('toPrepare', 0))
        ws.cell(row=idx, column=4, value=item.get('unit', 'portions'))
        ws.cell(row=idx, column=5, value=item.get('shelfLife', '-'))
        
        cost_per = item.get('costPerPortion', 0)
        total_item = item.get('totalCost', 0)
        
        ws.cell(row=idx, column=6, value=cost_per)
        ws.cell(row=idx, column=6).number_format = '€#,##0.00'
        
        ws.cell(row=idx, column=7, value=total_item)
        ws.cell(row=idx, column=7).number_format = '€#,##0.00'
        
        ws.cell(row=idx, column=8, value=item.get('notes', ''))
        
        total_cost += total_item
        total_portions += item.get('toPrepare', 0)
        
        # Borders
        for col in range(1, 9):
            ws.cell(row=idx, column=col).border = border
    
    # Totals row
    totals_row = len(data) + 5
    totals_label = 'TOTALS' if locale == 'en' else 'TOTALI'
    ws.cell(row=totals_row, column=1, value=totals_label)
    ws.cell(row=totals_row, column=1).font = Font(bold=True)
    ws.cell(row=totals_row, column=3, value=total_portions)
    ws.cell(row=totals_row, column=3).font = Font(bold=True)
    ws.cell(row=totals_row, column=7, value=total_cost)
    ws.cell(row=totals_row, column=7).number_format = '€#,##0.00'
    ws.cell(row=totals_row, column=7).font = Font(bold=True)
    
    for col in range(1, 9):
        ws.cell(row=totals_row, column=col).fill = total_fill
        ws.cell(row=totals_row, column=col).border = border
    
    # Column widths
    ws.column_dimensions['A'].width = 25
    ws.column_dimensions['B'].width = 12
    ws.column_dimensions['C'].width = 12
    ws.column_dimensions['D'].width = 10
    ws.column_dimensions['E'].width = 12
    ws.column_dimensions['F'].width = 14
    ws.column_dimensions['G'].width = 14
    ws.column_dimensions['H'].width = 30
    
    # Save to bytes
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
