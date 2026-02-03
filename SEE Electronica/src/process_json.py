import json
import sys
import os

# Add the project root to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.services.json_mapper import JsonInvoiceMapper
from src.services.xml_builder import InvoiceXMLBuilder
from src.services.pdf_generator import InvoicePDFGenerator

def process_json(json_path):
    print(f"Reading JSON from: {json_path}")
    
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    print("Mapping JSON to Invoice model...")
    invoice = JsonInvoiceMapper.map(data)
    
    print("Building XML...")
    builder = InvoiceXMLBuilder()
    xml_content = builder.build(invoice)
    
    # Determine output path (same directory as JSON, but with .XML extension)
    base_path = os.path.splitext(json_path)[0]
    xml_path = base_path + ".XML"
    
    with open(xml_path, "wb") as f:
        f.write(xml_content)
        
    print(f"XML generated successfully at: {xml_path}")
    
    # Generate PDF
    print("Generating PDF...")
    pdf_path = base_path + ".PDF"
    pdf_gen = InvoicePDFGenerator(pdf_path)
    pdf_gen.generate(invoice)
    print(f"PDF generated successfully at: {pdf_path}")

    # 3. Sign XML
    from src.services.signer import XMLSigner
    from src.services.sender import SunatSender
    
    key_path = "c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/SEE Electronica/CDT/LLAMAPECERTIFICADODEMO20136564367_cert_out.pem"
    cert_path = "c:/Users/USUARIO/Mi unidad (eddiejhersson1@gmail.com)/Proyecto tkinter/SEE Electronica/CDT/LLAMAPECERTIFICADODEMO20136564367_cert_out.pem"
    
    print(f"Signing XML using {cert_path}...")
    signer = XMLSigner()
    try:
        signed_xml = signer.sign(xml_content, key_path, cert_path)
        # Overwrite the XML with the signed version
        with open(xml_path, "wb") as f:
            f.write(signed_xml)
        print(f"Signed XML saved to {xml_path}")
    except Exception as e:
        print(f"Signing failed: {e}")
        return

    # 4. Send to SUNAT
    sol_user = "20136564367MODDATOS"
    sol_pass = "MODDATOS"
    
    print(f"Sending to SUNAT Beta as {sol_user}...")
    sender = SunatSender(sol_user, sol_pass)
    
    filename = os.path.basename(xml_path)
    response = sender.send_bill(filename, signed_xml)
    
    if response.success:
        print("Invoice sent successfully!")
        zip_name = os.path.join(os.path.dirname(xml_path), f"R-{filename.replace('.XML', '.zip').replace('.xml', '.zip')}")
        with open(zip_name, "wb") as f:
            f.write(response.cdr_zip)
        print(f"CDR saved to {zip_name}")
    else:
        error_msg = f"Failed to send invoice: {response.message}"
        print(error_msg)
        with open("error_log.txt", "w") as log:
            log.write(error_msg)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        json_file = sys.argv[1]
        process_json(json_file)
    else:
        print("Please provide the path to the JSON file.")
