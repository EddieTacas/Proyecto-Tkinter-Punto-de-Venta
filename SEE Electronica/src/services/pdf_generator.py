from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from src.models.invoice import Invoice

class InvoicePDFGenerator:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self.styles = getSampleStyleSheet()
        
    def generate(self, invoice: Invoice):
        doc = SimpleDocTemplate(self.output_path, pagesize=A4,
                                rightMargin=1*cm, leftMargin=1*cm,
                                topMargin=1*cm, bottomMargin=1*cm)
        
        elements = []
        
        # 1. Header (Issuer Info & Invoice ID)
        # In a real app, you'd add a logo here
        
        # Issuer Info
        issuer_text = f"""
        <b>{invoice.supplier.registration_name}</b><br/>
        {invoice.supplier.address_line}<br/>
        RUC: {invoice.supplier.id}
        """
        p_issuer = Paragraph(issuer_text, self.styles["Normal"])
        
        # Invoice Box
        invoice_type_name = "FACTURA ELECTRÓNICA" if invoice.invoice_type_code == "01" else "BOLETA DE VENTA ELECTRÓNICA"
        box_text = f"""
        <font size=12><b>R.U.C. {invoice.supplier.id}</b></font><br/><br/>
        <font size=14><b>{invoice_type_name}</b></font><br/><br/>
        <font size=12><b>{invoice.id}</b></font>
        """
        p_box = Paragraph(box_text, ParagraphStyle(name='Box', alignment=1, borderPadding=5))
        
        # Header Table
        header_data = [[p_issuer, "", p_box]]
        header_table = Table(header_data, colWidths=[10*cm, 1*cm, 7*cm])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0,0), (-1,-1), 'TOP'),
            ('BOX', (2,0), (2,0), 1, colors.black),
            ('ALIGN', (2,0), (2,0), 'CENTER'),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))
        
        # 2. Customer Info
        customer_text = f"""
        <b>Fecha de Emisión:</b> {invoice.issue_date}<br/>
        <b>Señor(es):</b> {invoice.customer.registration_name}<br/>
        <b>{invoice.customer.id_scheme == '6' and 'RUC' or 'DNI'}:</b> {invoice.customer.id}<br/>
        <b>Dirección:</b> {invoice.customer.address_line}<br/>
        <b>Moneda:</b> {invoice.currency_code}
        """
        elements.append(Paragraph(customer_text, self.styles["Normal"]))
        elements.append(Spacer(1, 0.5*cm))
        
        # 3. Items Table
        data = [['Cant.', 'Unidad', 'Descripción', 'V. Unitario', 'Precio Total']]
        
        for line in invoice.lines:
            data.append([
                str(line.quantity),
                line.unit_code,
                Paragraph(line.description, self.styles["Normal"]), # Wrap text
                f"{line.price_unit_amount:.2f}",
                f"{line.line_extension_amount:.2f}" # Or price_amount depending on logic
            ])
            
        table = Table(data, colWidths=[2*cm, 2*cm, 9*cm, 3*cm, 3*cm])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.lightgrey),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('ALIGN', (2,0), (2,-1), 'LEFT'), # Description left aligned
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 12),
            ('GRID', (0,0), (-1,-1), 1, colors.black),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.5*cm))
        
        # 4. Totals
        totals_data = []
        
        # Op. Gravada
        if invoice.tax_total_amount > 0:
             totals_data.append(['Op. Gravada', f"{invoice.legal_monetary_total_line_extension_amount:.2f}"])
             totals_data.append(['IGV (18%)', f"{invoice.tax_total_amount:.2f}"])
        
        totals_data.append(['Importe Total', f"{invoice.legal_monetary_total_payable_amount:.2f}"])
        
        totals_table = Table(totals_data, colWidths=[15*cm, 4*cm])
        totals_table.setStyle(TableStyle([
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'RIGHT'),
            ('FONTNAME', (0,-1), (-1,-1), 'Helvetica-Bold'), # Bold total
            ('BOX', (1,0), (1,-1), 1, colors.black),
        ]))
        elements.append(totals_table)
        elements.append(Spacer(1, 0.5*cm))
        
        # 5. Amount in Words (Note)
        if invoice.note:
             elements.append(Paragraph(f"<b>SON:</b> {invoice.note}", self.styles["Normal"]))
        
        # 6. Footer / Hash (Placeholder)
        elements.append(Spacer(1, 1*cm))
        elements.append(Paragraph("Representación Impresa de la Factura Electrónica", self.styles["Italic"]))
        
        doc.build(elements)
