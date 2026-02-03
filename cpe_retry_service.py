import time
import threading
import database
import xml_generator
import whatsapp_manager
import os

class CPERetryService:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.running = False
        self.interval = 3600 # 1 hour
        self.see_dir = os.path.join(base_dir, "SEE Electronica")

    def start(self):
        if not self.running:
            self.running = True
            thread = threading.Thread(target=self.retry_loop, daemon=True)
            thread.start()
            print("CPE Retry Service Started.")

    def retry_loop(self):
        while self.running:
            try:
                self.process_retries()
            except Exception as e:
                print(f"Error in CPE Retry Loop: {e}")
            
            time.sleep(self.interval)

    def process_retries(self):
        print("Checking for pending invoices...")
        pending_invoices = database.get_pending_invoices_for_retry()
        
        if not pending_invoices:
            print("No pending invoices found.")
            return

        xml_gen = xml_generator.XMLGenerator(self.see_dir)
        
        for invoice in pending_invoices:
            try:
                sale_id = invoice['id']
                doc_type_full = invoice['document_type']
                doc_number = invoice['document_number']
                issuer_id = invoice['issuer_id'] # Note: 'issuer_id' key from dict(row)
                
                print(f"Retrying Sale ID {sale_id}: {doc_number} ({doc_type_full})")
                
                # Get Issuer Data
                issuer = database.get_issuer_by_id(issuer_id)
                if not issuer:
                    print(f"Issuer {issuer_id} not found for Sale {sale_id}. Skipping.")
                    continue

                # Prepare Data for check_cdr_status
                # We need doc type code (01, 03) and series/number split.
                if "FACTURA" in doc_type_full.upper():
                    type_code = "01"
                elif "BOLETA" in doc_type_full.upper():
                    type_code = "03"
                else:
                    print(f"Unknown type {doc_type_full}. Skipping.")
                    continue

                if "-" in doc_number:
                    series, number = doc_number.split("-")
                else:
                    print(f"Invalid format {doc_number}. Skipping.")
                    continue

                # Check Status
                result = xml_gen.check_cdr_status(issuer, type_code, series, number)
                
                if result['success']:
                    xml_resp = result['response']
                    status = "PENDIENTE"
                    note = ""
                    
                    if "applicationResponse" in xml_resp:
                        status = "ACEPTADO"
                        note = "Aceptado (Validado por Retry Service)"
                        # TODO: Extract CDR and save?
                        # For now, just update status.
                        
                    elif "Fault" in xml_resp:
                        status = "RECHAZADO"
                        if "<faultstring>" in xml_resp:
                             note = xml_resp.split("<faultstring>")[1].split("</faultstring>")[0]
                        elif ":faultstring>" in xml_resp:
                             note = xml_resp.split(":faultstring>")[1].split("</")[0]
                        else:
                             note = "Error SOAP desconocido (Retry)"
                        
                        # Trigger WhatsApp Alert
                        alert_receivers = issuer.get('cpe_alert_receivers')
                        if alert_receivers:
                             try:
                                 msg = f"⚠ *Alerta CPE Rechazado (Reintento)*\n📄 *{doc_number}*\n❌ *Error*: {note}"
                                 for receiver in alert_receivers.split(','):
                                     r = receiver.strip()
                                     if r:
                                         whatsapp_manager.baileys_manager.send_message(r, msg)
                             except Exception as e_wa:
                                 print(f"WA Alert Error: {e_wa}")
                                 
                    elif "ticket" in xml_resp:
                        status = "PENDIENTE" # Still pending
                        note = "Aún en proceso (SUNAT)"
                    
                    # Update DB if status changed (or even if verified pending to update timestamp/note)
                    if status != "PENDIENTE" or (status == "PENDIENTE" and invoice['sunat_status'] == "ERROR_CONEXION"):
                        database.update_sale_sunat_status(sale_id, status, note)
                        print(f"Updated Sale {sale_id} to {status}")
                
                else:
                    print(f"Retry failed for {sale_id}: {result.get('error')}")
            
            except Exception as e_inv:
                print(f"Error processing invoice {invoice.get('id')}: {e_inv}")
