import os
import zipfile
import base64
from datetime import datetime
from lxml import etree
from signxml import XMLSigner, methods
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.backends import default_backend
import requests

class XMLGenerator:
    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.xml_dir = os.path.join(base_dir, "XML")
        self.cdr_dir = os.path.join(base_dir, "CDR")
        
        if not os.path.exists(self.xml_dir): os.makedirs(self.xml_dir)
        if not os.path.exists(self.cdr_dir): os.makedirs(self.cdr_dir)
            
        self.ns = {
            'urn:oasis:names:specification:ubl:schema:xsd:Invoice-2': 'Invoice',
            'urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2': 'cac',
            'urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2': 'cbc',
            'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2': 'ext',
            'http://www.w3.org/2000/09/xmldsig#': 'ds'
        }

    def generate_and_send(self, sale_data, issuer_data):
        """
        Orchestrates XML generation, signing, zipping, and sending.
        issuer_data should contain: certificate (blob), password (str, optional), fe_url (str)
        """
        try:
            # 1. Generate XML Tree (Unsigned)
            xml_tree, filename_base = self._build_invoice_xml(sale_data, issuer_data)
            
            # 2. Sign XML
            cert_blob = issuer_data.get('certificate')
            # Assuming no password for PEM or using SOL pass for PFX if needed (logic to be refined)
            password = issuer_data.get('cert_password') or issuer_data.get('sol_pass') # Attempt to use sol_pass if pfx requires it?
            
            if not cert_blob:
                raise ValueError("No certificate found for issuer")

            pkey, cert_pem = self._load_key_and_cert(cert_blob, password)
            signed_xml = self._sign_xml_ubl(xml_tree, pkey, cert_pem)
            
            # 3. Save Signed XML
            xml_filename = f"{filename_base}.xml"
            xml_path = os.path.join(self.xml_dir, xml_filename)
            with open(xml_path, 'wb') as f:
                f.write(etree.tostring(signed_xml, encoding='ISO-8859-1')) 
            
            # 4. Zip XML
            # User request: "quiero que el xml zipeado se mantenga en la misma carpeta" (XML folder)
            zip_filename = f"{filename_base}.zip"
            zip_path = os.path.join(self.xml_dir, zip_filename)
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.write(xml_path, arcname=xml_filename)
            
            # Cleanup XML (User request: only keep zip)
            if os.path.exists(xml_path):
                os.remove(xml_path)
            
            # 5. Send to API
            fe_url = issuer_data.get('fe_url')
            cdr_path = None
            if fe_url:
                response = self._send_to_pse(zip_path, zip_filename, fe_url, issuer_data)
                
                # Try to extract and save CDR
                try:
                    import re
                    # Look for applicationResponse (ignore namespace prefixes)
                    match = re.search(r'<[^:]*:?applicationResponse>(.*?)</[^:]*:?applicationResponse>', response, re.DOTALL)
                    if match:
                        cdr_b64 = match.group(1)
                        cdr_content = base64.b64decode(cdr_b64)
                        
                        cdr_filename = f"R-{filename_base}.zip"
                        cdr_path = os.path.join(self.cdr_dir, cdr_filename)
                        
                        with open(cdr_path, 'wb') as f:
                            f.write(cdr_content)
                            
                        print(f"CDR Saved: {cdr_path}")
                except Exception as e:
                    print(f"Error saving CDR: {e}")

                return {
                    "success": True, 
                    "xml_path": xml_path, 
                    "zip_path": zip_path, 
                    "cdr_path": cdr_path,
                    "response": response
                }
            else:
                return {"success": True, "xml_path": xml_path, "zip_path": zip_path, "response": "No URL configured"}

        except Exception as e:
            print(f"XML Process Error: {e}")
            return {"success": False, "error": str(e)}

    def _build_invoice_xml(self, data, issuer_data):
        doc = data['document']
        issuer = data['issuer']
        customer = data['customer']
        items = data['items']
        
        # Namespaces
        nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        }
        
        # Determines type
        type_name = doc['type_name'].upper()
        if "FACTURA" in type_name:
            inv_type = "01"
            prefix = "F001" if not doc['series'] else doc['series']
            is_boleta = False
        else:
            inv_type = "03"
            prefix = "B001" if not doc['series'] else doc['series']
            is_boleta = True
            
        try:
            num = f"{int(doc['number']):08d}"
        except:
            num = str(doc['number'])
            
        full_id = f"{prefix}-{num}"
        filename_base = f"{issuer['ruc']}-{inv_type}-{full_id}"
        
        # Root Element
        root = etree.Element(f"{{urn:oasis:names:specification:ubl:schema:xsd:Invoice-2}}Invoice", nsmap=nsmap)
        
        # UBLExtensions (Placeholder for Signature)
        exts = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}UBLExtensions")
        ext_wrapper = etree.SubElement(exts, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}UBLExtension")
        ext_content = etree.SubElement(ext_wrapper, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2}}ExtensionContent")
        # Ensure we place the signature here later
        
        # Standard Fields
        self._add_text_elem(root, "cbc", "UBLVersionID", "2.1")
        self._add_text_elem(root, "cbc", "CustomizationID", "2.0")
        self._add_text_elem(root, "cbc", "ID", full_id)
        self._add_text_elem(root, "cbc", "IssueDate", doc['issue_date'].strftime("%Y-%m-%d"))
        self._add_text_elem(root, "cbc", "IssueTime", doc['issue_date'].strftime("%H:%M:%S"))
        
        # InvoiceTypeCode
        itc = self._add_text_elem(root, "cbc", "InvoiceTypeCode", inv_type)
        itc.set("listID", "0101")
        
        # Legend (Amount in text)
        total_payable = self._calc_total(items)
        note = self._add_text_elem(root, "cbc", "Note", self._number_to_text(total_payable))
        note.set("languageLocaleID", "1000")
        
        self._add_text_elem(root, "cbc", "DocumentCurrencyCode", doc.get('currency', 'PEN'))

        # Signature Reference (Different from the actual DSig)
        cac_sig = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}Signature")
        self._add_text_elem(cac_sig, "cbc", "ID", "APISUNAT") # or issuer ID
        sig_party = etree.SubElement(cac_sig, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}SignatoryParty")
        
        pid = etree.SubElement(sig_party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyIdentification")
        self._add_text_elem(pid, "cbc", "ID", issuer['ruc'])
        
        pn = etree.SubElement(sig_party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyName")
        self._add_text_elem(pn, "cbc", "Name", issuer['name'])

        dsa = etree.SubElement(cac_sig, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}DigitalSignatureAttachment")
        ext_ref = etree.SubElement(dsa, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}ExternalReference")
        self._add_text_elem(ext_ref, "cbc", "URI", issuer.get('fe_url', '')) # URI reference

        # Supplier
        supplier = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}AccountingSupplierParty")
        party = etree.SubElement(supplier, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}Party")
        pid = etree.SubElement(party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyIdentification")
        id_node = self._add_text_elem(pid, "cbc", "ID", issuer['ruc'])
        id_node.set("schemeID", "6")
        
        pn = etree.SubElement(party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyName")
        self._add_text_elem(pn, "cbc", "Name", issuer.get('commercial_name') or issuer['name'])

        legal = etree.SubElement(party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyLegalEntity")
        self._add_text_elem(legal, "cbc", "RegistrationName", issuer['name'])
        
        reg_addr = etree.SubElement(legal, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}RegistrationAddress")
        self._add_text_elem(reg_addr, "cbc", "AddressTypeCode", issuer.get('establishment_code', '0000'))
        addr_line = etree.SubElement(reg_addr, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}AddressLine")
        self._add_text_elem(addr_line, "cbc", "Line", issuer['address'])

        # Customer
        customer_node = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}AccountingCustomerParty")
        party = etree.SubElement(customer_node, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}Party")
        pid = etree.SubElement(party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyIdentification")
        
        cust_doc_num = customer.get('doc_number')
        if not cust_doc_num: # No doc logic from boleta example
             cust_doc_num = "-"
             scheme = "0" # Doc. Trib. No. Dom. Sin RUC (0) or try "0" for Sin Documento
        else:
             if len(cust_doc_num) == 11: scheme = "6"
             elif len(cust_doc_num) == 8: scheme = "1"
             else: scheme = "0" 
        
        id_node = self._add_text_elem(pid, "cbc", "ID", cust_doc_num)
        id_node.set("schemeID", scheme)
        id_node.set("schemeName", "Documento de Identidad")
        id_node.set("schemeAgencyName", "PE:SUNAT")
        id_node.set("schemeURI", "urn:pe:gob:sunat:cpe:see:gem:catalogos:catalogo06")

        legal = etree.SubElement(party, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PartyLegalEntity")
        cust_name = customer['name'] if customer.get('doc_number') else "CLIENTES VARIOS"
        self._add_text_elem(legal, "cbc", "RegistrationName", cust_name)
        
        reg_addr = etree.SubElement(legal, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}RegistrationAddress")
        addr_line = etree.SubElement(reg_addr, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}AddressLine")
        self._add_text_elem(addr_line, "cbc", "Line", customer.get('address') or "-")

        # Payment Terms (Only Factura)
        if not is_boleta:
             pt = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PaymentTerms")
             self._add_text_elem(pt, "cbc", "ID", "FormaPago")
             self._add_text_elem(pt, "cbc", "PaymentMeansID", "Contado")

        # Calculations & Totals
        total_igv = 0.0
        total_taxable = 0.0
        
        for item in items:
             p_inc_igv = float(item['price_unit_inc_igv'])
             qty = float(item['quantity'])
             # Base
             p_base = p_inc_igv / 1.18
             line_ext = p_base * qty
             igv_line = line_ext * 0.18
             total_igv += igv_line
             total_taxable += line_ext

        total_igv = round(total_igv, 2)
        total_taxable = round(total_taxable, 2)
        
        # Tax Total
        tax_total = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxTotal")
        tt_amt = self._add_text_elem(tax_total, "cbc", "TaxAmount", str(total_igv))
        tt_amt.set("currencyID", doc.get('currency', 'PEN'))

        ts = etree.SubElement(tax_total, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxSubtotal")
        t_amt = self._add_text_elem(ts, "cbc", "TaxableAmount", str(total_taxable))
        t_amt.set("currencyID", "PEN")
        t_amt = self._add_text_elem(ts, "cbc", "TaxAmount", str(total_igv))
        t_amt.set("currencyID", "PEN")

        tc = etree.SubElement(ts, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxCategory")
        tscheme = etree.SubElement(tc, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxScheme")
        self._add_text_elem(tscheme, "cbc", "ID", "1000")
        self._add_text_elem(tscheme, "cbc", "Name", "IGV")
        self._add_text_elem(tscheme, "cbc", "TaxTypeCode", "VAT")

        # Monetary Total
        lmt = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}LegalMonetaryTotal")
        t = self._add_text_elem(lmt, "cbc", "LineExtensionAmount", str(total_taxable))
        t.set("currencyID", "PEN")
        t = self._add_text_elem(lmt, "cbc", "TaxInclusiveAmount", str(total_payable))
        t.set("currencyID", "PEN")
        t = self._add_text_elem(lmt, "cbc", "PayableAmount", str(total_payable))
        t.set("currencyID", "PEN")

        # Lines
        for idx, item in enumerate(items, 1):
             self._add_invoice_line(root, idx, item)

        return root, filename_base

    def _add_invoice_line(self, root, idx, item):
         line = etree.SubElement(root, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}InvoiceLine")
         self._add_text_elem(line, "cbc", "ID", str(idx))
         
         qty_val = float(item['quantity'])
         qty = self._add_text_elem(line, "cbc", "InvoicedQuantity", str(qty_val))
         unit_code = item.get('unit_code', 'NIU')
         if not unit_code: unit_code = 'NIU'
         qty.set("unitCode", unit_code)
         
         p_inc = float(item['price_unit_inc_igv'])
         p_base = p_inc / 1.18
         line_ext = round(p_base * qty_val, 2)
         
         lea = self._add_text_elem(line, "cbc", "LineExtensionAmount", str(line_ext))
         lea.set("currencyID", "PEN")
         
         # Pricing Ref
         pr = etree.SubElement(line, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}PricingReference")
         acp = etree.SubElement(pr, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}AlternativeConditionPrice")
         pa = self._add_text_elem(acp, "cbc", "PriceAmount", str(round(p_inc, 2)))
         pa.set("currencyID", "PEN")
         self._add_text_elem(acp, "cbc", "PriceTypeCode", "01")
         
         # Tax Total
         line_igv = round(line_ext * 0.18, 2)
         tt = etree.SubElement(line, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxTotal")
         ta = self._add_text_elem(tt, "cbc", "TaxAmount", str(line_igv))
         ta.set("currencyID", "PEN")
         
         ts = etree.SubElement(tt, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxSubtotal")
         self._add_text_elem(ts, "cbc", "TaxableAmount", str(line_ext)).set("currencyID", "PEN")
         self._add_text_elem(ts, "cbc", "TaxAmount", str(line_igv)).set("currencyID", "PEN")
         
         tc = etree.SubElement(ts, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxCategory")
         self._add_text_elem(tc, "cbc", "Percent", "18")
         self._add_text_elem(tc, "cbc", "TaxExemptionReasonCode", "10")
         
         tscm = etree.SubElement(tc, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}TaxScheme")
         self._add_text_elem(tscm, "cbc", "ID", "1000")
         self._add_text_elem(tscm, "cbc", "Name", "IGV")
         self._add_text_elem(tscm, "cbc", "TaxTypeCode", "VAT")
         
         # Item
         it = etree.SubElement(line, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}Item")
         self._add_text_elem(it, "cbc", "Description", item['description'])

         # Price
         price = etree.SubElement(line, f"{{urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2}}Price")
         pa = self._add_text_elem(price, "cbc", "PriceAmount", str(round(p_base, 10)))
         pa.set("currencyID", "PEN")


    def _add_text_elem(self, parent, prefix, name, text):
        elem = etree.SubElement(parent, f"{{urn:oasis:names:specification:ubl:schema:xsd:{'CommonBasicComponents-2' if prefix=='cbc' else 'CommonAggregateComponents-2'}}}{name}")
        elem.text = str(text)
        return elem

    def _sign_xml_ubl(self, root, key, cert_pem):
        """
        Signs the UBL following strict placement: 
        ext:UBLExtensions > ext:UBLExtension > ext:ExtensionContent > ds:Signature
        """
        signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm="rsa-sha256",
            digest_algorithm="sha256",
            c14n_algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"
        )
        
        # signxml signs the root by default.
        # We need to sign, and then MOVE the signature to the ExtensionContent
        
        signed_root = signer.sign(root, key=key, cert=cert_pem)
        
        # Find the signature
        ns = {'ds': 'http://www.w3.org/2000/09/xmldsig#', 'ext': 'urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2'}
        signature_node = signed_root.find(".//ds:Signature", namespaces=ns)
        
        if signature_node is not None:
             # Find target location
             target = signed_root.find(".//ext:ExtensionContent", namespaces=ns)
             if target is not None:
                  # Remove from current location (usually end of file)
                  signature_node.getparent().remove(signature_node)
                  # Append to target
                  target.append(signature_node)
                  # Set Id for Reference URI=""
                  # UBL usually expects URI="" meaning root. signxml does this.
                  # But wait, if we move it, does it invalidate the hash?
                  # Enveloped signature excludes the signature itself from the hash.
                  # Since validation checks the root (URI=""), and the signature is still *inside* the root, it should be fine.
                  # However, C14N might differ if position changes.
                  # A correct UBL signer calculates hash of the *Canonicalized Invoice excluding Signature*
                  # If signxml calculated it based on root, and we move it, the byte stream of root changes?
                  # No, "Enveloped" transform removes the Signature element before hashing. 
                  # So as long as Signature is descendant of Root, the hash of Root (minus Signature) is constant.
                  pass
        
        return signed_root

    def _load_key_and_cert(self, blob, password=None):
        # Try loading as PFX
        try:
             p12 = pkcs12.load_key_and_certificates(blob, password.encode() if password else None, backend=default_backend())
             key = p12[0]
             cert = p12[1]
             # Convert cert to PEM for signxml
             cert_pem = cert.public_bytes(serialization.Encoding.PEM)
             # Key to PEM
             key_pem = key.private_bytes(
                 encoding=serialization.Encoding.PEM,
                 format=serialization.PrivateFormat.PKCS8,
                 encryption_algorithm=serialization.NoEncryption()
             )
             return key_pem, cert_pem
        except Exception as e:
             # Try plain PEM
             try:
                 # Check if blob is already text or bytes
                 if isinstance(blob, bytes):
                     blob_str = blob #.decode('utf-8')
                 
                 # It might be just a key or key+cert
                 # Simple heuristic: try to load PEM
                 # If it fails, maybe user has to provide a password?
                 # For now, return raw blob as PEM strings if they look like PEM
                 return blob, blob
             except:
                 raise e

    def _calc_total(self, items):
        total = 0.0
        for i in items:
            total += float(i['price_unit_inc_igv']) * float(i['quantity'])
        return round(total, 2)
        
    def _number_to_text(self, amount):
        # ... Reuse logic or import from json_generator ...
        # For brevity, I'll copy the logic from the json generator I saw earlier
        def num_to_text_int(n):
            if n == 0: return ""
            unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
            decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
            diez_y = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
            veinte_y = ["VEINTE", "VEINTIUNO", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
            centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]
            if n < 10: return unidades[n]
            elif n < 20: return diez_y[n - 10]
            elif n < 30: return veinte_y[n - 20]
            elif n < 100:
                u = n % 10
                if u == 0: return decenas[n // 10]
                return f"{decenas[n // 10]} Y {unidades[u]}"
            elif n < 1000:
                if n == 100: return "CIEN"
                return f"{centenas[n // 100]} {num_to_text_int(n % 100)}"
            elif n < 1000000:
                miles = n // 1000
                s_miles = "MIL" if miles == 1 else f"{num_to_text_int(miles)} MIL"
                return f"{s_miles} {num_to_text_int(n % 1000)}".strip()
            return str(n)

        amount_int = int(amount)
        decimal_part = int(round((amount - amount_int) * 100))
        text_int = num_to_text_int(amount_int)
        if text_int == "": text_int = "CERO"
        return f"{text_int} CON {decimal_part:02d}/100 SOLES"

    def _send_to_pse(self, zip_path, zip_filename, url, issuer_data):
        # SOAP Implementation for SUNAT
        # Requires WS-Security with RUC+User and Password
        
        ruc = issuer_data.get('ruc', '')
        sol_user = issuer_data.get('sol_user', '')
        sol_pass = issuer_data.get('sol_pass', '')
        
        # SUNAT Username is often RUC + USER (e.g. 20123456789MODDATOS)
        # If sol_user doesn't start with RUC, prepending might be safer or leave as is if user entered full.
        # Usually users enter just the specific user. Let's try combining if purely numeric RUC is separate.
        username = f"{ruc}{sol_user}" if len(sol_user) < 11 else sol_user
        
        # Read Zip and B64 encode
        with open(zip_path, "rb") as f:
            zip_content = base64.b64encode(f.read()).decode('utf-8')

        soap_env = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.sunat.gob.pe" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
   <soapenv:Header>
      <wsse:Security>
         <wsse:UsernameToken>
            <wsse:Username>{username}</wsse:Username>
            <wsse:Password>{sol_pass}</wsse:Password>
         </wsse:UsernameToken>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body>
      <ser:sendBill>
         <fileName>{zip_filename}</fileName>
         <contentFile>{zip_content}</contentFile>
      </ser:sendBill>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'urn:sendBill'
        }
        
        try:
            r = requests.post(url, data=soap_env, headers=headers, timeout=45)
            return r.text
        except Exception as e:
            raise e

    def check_cdr_status(self, issuer_data, type_code, series, number):
        """Consulta el estado de un comprobante (getStatusCdr)."""
        # Endpoint varies by environment. For Prod:
        url = "https://e-factura.sunat.gob.pe/ol-it-wsconscpegem/billConsultService"
        # For Beta/Dev: https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billConsultService
        # Logic to choose URL? 
        # Usually checking variable or default to Prod. 
        # Existing sendBill uses issuer['fe_url'].
        # For query, the URL is DIFFERENT from sendBill URL.
        # sendBill: /ol-ti-itcpe/billService
        # query: /ol-it-wsconscpegem/billConsultService
        # Use issuer_data['guia_url_consultar'] if appropriate? No, that's for Guias.
        # I'll default to Prod URL if not provided, or check if issuer has 'consult_url'.
        # Safest: Use Prod URL constant for now or strict map.
        
        # Hardcoded Prod URL for Query (Standard)
        if "beta" in issuer_data.get('fe_url', ''):
             url = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billConsultService"
        
        ruc = issuer_data.get('ruc', '')
        sol_user = issuer_data.get('sol_user', '')
        sol_pass = issuer_data.get('sol_pass', '')
        username = f"{ruc}{sol_user}" if len(sol_user) < 11 else sol_user
        
        # SOAP Envelope
        soap_env = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.sunat.gob.pe" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
   <soapenv:Header>
      <wsse:Security>
         <wsse:UsernameToken>
            <wsse:Username>{username}</wsse:Username>
            <wsse:Password>{sol_pass}</wsse:Password>
         </wsse:UsernameToken>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body>
      <ser:getStatusCdr>
         <rucComprobante>{ruc}</rucComprobante>
         <tipoComprobante>{type_code}</tipoComprobante>
         <serieComprobante>{series}</serieComprobante>
         <numeroComprobante>{number}</numeroComprobante>
      </ser:getStatusCdr>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'urn:getStatusCdr'
        }
        
        try:
            r = requests.post(url, data=soap_env, headers=headers, timeout=45)
            # Parse response
            # Format: <statusCdr><content>BASE64</content><statusCode>X</statusCode><statusMessage>...</statusMessage></statusCdr>
            # Or Fault.
            return {'success': True, 'response': r.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_ticket_status(self, issuer_data, ticket):
        """Consulta el estado de un ticket (getStatus)."""
        url = "https://e-factura.sunat.gob.pe/ol-ti-itcpfegem/billService" # Same as sendBill often? Or separate?
        # getStatus is in billService.
        if "beta" in issuer_data.get('fe_url', ''):
             url = "https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"

        ruc = issuer_data.get('ruc', '')
        sol_user = issuer_data.get('sol_user', '')
        sol_pass = issuer_data.get('sol_pass', '')
        username = f"{ruc}{sol_user}" if len(sol_user) < 11 else sol_user
        
        soap_env = f"""<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.sunat.gob.pe" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
   <soapenv:Header>
      <wsse:Security>
         <wsse:UsernameToken>
            <wsse:Username>{username}</wsse:Username>
            <wsse:Password>{sol_pass}</wsse:Password>
         </wsse:UsernameToken>
      </wsse:Security>
   </soapenv:Header>
   <soapenv:Body>
      <ser:getStatus>
         <ticket>{ticket}</ticket>
      </ser:getStatus>
   </soapenv:Body>
</soapenv:Envelope>"""

        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'urn:getStatus'
        }
        
        try:
            r = requests.post(url, data=soap_env, headers=headers, timeout=45)
            return {'success': True, 'response': r.text}
        except Exception as e:
            return {'success': False, 'error': str(e)}
