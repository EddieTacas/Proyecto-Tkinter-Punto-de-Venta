import os
from datetime import date, time
from src.models.invoice import Invoice, Party, InvoiceLine, TaxSubtotal
from src.services.xml_builder import InvoiceXMLBuilder
from src.services.signer import XMLSigner
from src.services.sender import SunatSender

def main():
    # 1. Create Invoice Data (Matching the example XML)
    invoice = Invoice(
        id="B001-00000004",
        issue_date=date(2025, 11, 30),
        issue_time=time(17, 26, 49),
        invoice_type_code="03", # Boleta
        note="CIENTO CINCUENTA CON 00/100 SOLES",
        currency_code="PEN",
        supplier=Party(
            id="20136564367",
            registration_name="SUPERINT ADMINIST.PRIV.FONDOS DE PENSION",
            address_line="AV. PASEO DE LA REPUBLIC NRO. 3285 SAN ISIDRO LIMA LIMA"
        ),
        customer=Party(
            id="20600811658",
            registration_name="EXP. COMPANY SOCIEDAD ANONIMA CERRADA - EXP COMPANY S.A.C.",
            address_line="JR. AMERICA NRO. 489 URB. EL PORVENIR LA VICTORIA LIMA LIMA"
        ),
        tax_total_amount=22.88,
        legal_monetary_total_line_extension_amount=127.12,
        legal_monetary_total_tax_inclusive_amount=150.00,
        legal_monetary_total_payable_amount=150.00
    )
    
    # Add Tax Subtotal
    invoice.tax_subtotals.append(TaxSubtotal(
        taxable_amount=127.12,
        tax_amount=22.88,
        tax_category_percent=18.0
    ))
    
    # Add Lines
    invoice.lines.append(InvoiceLine(
        id="1",
        quantity=1.0,
        unit_code="NIU",
        line_extension_amount=25.42,
        price_amount=30.00,
        tax_amount=4.58,
        taxable_amount=25.42,
        description="polo de jersey 30/1",
        price_unit_amount=25.4237288136
    ))
    
    invoice.lines.append(InvoiceLine(
        id="2",
        quantity=2.0,
        unit_code="NIU",
        line_extension_amount=101.69,
        price_amount=60.00,
        tax_amount=18.31,
        taxable_amount=101.69,
        description="shores",
        price_unit_amount=50.8474576271
    ))
    
    # 2. Build XML
    print("Building XML...")
    builder = InvoiceXMLBuilder()
    xml_content = builder.build(invoice)
    
    # Save unsigned XML for inspection
    with open("invoice_unsigned.xml", "wb") as f:
        f.write(xml_content)
    print("Unsigned XML saved to invoice_unsigned.xml")
    
    # 3. Sign XML
    # NOTE: Using the provided PEM file for both key and cert (assuming it contains the private key)
    # If the key is in a separate file, update key_path accordingly.
    key_path = "c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/SEE Electronica/CDT/LLAMAPECERTIFICADODEMO20136564367_cert_out.pem"
    cert_path = "c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/SEE Electronica/CDT/LLAMAPECERTIFICADODEMO20136564367_cert_out.pem"
    
    print(f"Signing XML using {cert_path}...")
    signer = XMLSigner()
    try:
        # Assuming no password for the PEM key or it's unencrypted
        signed_xml = signer.sign(xml_content, key_path, cert_path)
        with open("invoice_signed.xml", "wb") as f:
            f.write(signed_xml)
        print("Signed XML saved to invoice_signed.xml")
    except Exception as e:
        print(f"Signing failed: {e}")
        # Stop here if signing fails
        return
        
    # 4. Send to SUNAT
    # Using standard BETA credentials: RUC + MODDATOS
    sol_user = "20136564367MODDATOS"
    sol_pass = "MODDATOS"
    
    print(f"Sending to SUNAT Beta as {sol_user}...")
    sender = SunatSender(sol_user, sol_pass)
    
    # Filename format: RUC-TIPO-SERIE-CORRELATIVO.xml
    filename = f"{invoice.supplier.id}-{invoice.invoice_type_code}-{invoice.id}.xml"
    
    response = sender.send_bill(filename, signed_xml)
    
    if response.success:
        print("Invoice sent successfully!")
        zip_name = f"R-{filename.replace('.xml', '.zip')}"
        with open(zip_name, "wb") as f:
            f.write(response.cdr_zip)
        print(f"CDR saved to {zip_name}")
    else:
        print(f"Failed to send invoice: {response.message}")


if __name__ == "__main__":
    main()
