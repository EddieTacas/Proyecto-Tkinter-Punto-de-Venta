from lxml import etree
from src.models.invoice import Invoice

class InvoiceXMLBuilder:
    def __init__(self):
        self.nsmap = {
            None: "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2",
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        }
    
    def build(self, invoice: Invoice) -> bytes:
        root = etree.Element(f"{{{self.nsmap[None]}}}Invoice", nsmap=self.nsmap)
        
        # UBLExtensions (Placeholder for Signature)
        exts = etree.SubElement(root, f"{{{self.nsmap['ext']}}}UBLExtensions")
        ext = etree.SubElement(exts, f"{{{self.nsmap['ext']}}}UBLExtension")
        content = etree.SubElement(ext, f"{{{self.nsmap['ext']}}}ExtensionContent")
        # Signature will be inserted here later by the signer
        
        # Basic Info
        self._add_cbc(root, "UBLVersionID", invoice.ubl_version)
        self._add_cbc(root, "CustomizationID", invoice.customization_id)
        self._add_cbc(root, "ID", invoice.id)
        self._add_cbc(root, "IssueDate", invoice.issue_date.isoformat())
        self._add_cbc(root, "IssueTime", invoice.issue_time.strftime("%H:%M:%S"))
        self._add_cbc(root, "InvoiceTypeCode", invoice.invoice_type_code, listID="0101")
        if invoice.note:
            self._add_cbc(root, "Note", invoice.note, languageLocaleID="1000")
        self._add_cbc(root, "DocumentCurrencyCode", invoice.currency_code)
        
        # Signature Info (Placeholder structure for SUNAT)
        sig = etree.SubElement(root, f"{{{self.nsmap['cac']}}}Signature")
        self._add_cbc(sig, "ID", invoice.supplier.id) # Usually same as issuer
        signatory = etree.SubElement(sig, f"{{{self.nsmap['cac']}}}SignatoryParty")
        party_id = etree.SubElement(signatory, f"{{{self.nsmap['cac']}}}PartyIdentification")
        self._add_cbc(party_id, "ID", invoice.supplier.id)
        party_name = etree.SubElement(signatory, f"{{{self.nsmap['cac']}}}PartyName")
        self._add_cbc(party_name, "Name", invoice.supplier.registration_name)
        
        digital_sig_att = etree.SubElement(sig, f"{{{self.nsmap['cac']}}}DigitalSignatureAttachment")
        ext_ref = etree.SubElement(digital_sig_att, f"{{{self.nsmap['cac']}}}ExternalReference")
        self._add_cbc(ext_ref, "URI", f"#SignatureSP") # Reference to the signature ID
        
        # Supplier
        self._build_supplier(root, invoice.supplier)
        
        # Customer
        self._build_customer(root, invoice.customer)
        
        # Tax Total
        self._build_tax_total(root, invoice)
        
        # Legal Monetary Total
        self._build_legal_monetary_total(root, invoice)
        
        # Invoice Lines
        for line in invoice.lines:
            self._build_invoice_line(root, line)
            
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")

    def _add_cbc(self, parent, tag, value, **attribs):
        elem = etree.SubElement(parent, f"{{{self.nsmap['cbc']}}}{tag}", attrib=attribs)
        elem.text = str(value)
        return elem

    def _build_supplier(self, parent, supplier):
        asp = etree.SubElement(parent, f"{{{self.nsmap['cac']}}}AccountingSupplierParty")
        party = etree.SubElement(asp, f"{{{self.nsmap['cac']}}}Party")
        
        pid = etree.SubElement(party, f"{{{self.nsmap['cac']}}}PartyIdentification")
        self._add_cbc(pid, "ID", supplier.id, schemeID=supplier.id_scheme)
        
        ple = etree.SubElement(party, f"{{{self.nsmap['cac']}}}PartyLegalEntity")
        self._add_cbc(ple, "RegistrationName", supplier.registration_name)
        
        reg_addr = etree.SubElement(ple, f"{{{self.nsmap['cac']}}}RegistrationAddress")
        self._add_cbc(reg_addr, "AddressTypeCode", supplier.address_type_code)
        addr_line = etree.SubElement(reg_addr, f"{{{self.nsmap['cac']}}}AddressLine")
        self._add_cbc(addr_line, "Line", supplier.address_line)

    def _build_customer(self, parent, customer):
        acp = etree.SubElement(parent, f"{{{self.nsmap['cac']}}}AccountingCustomerParty")
        party = etree.SubElement(acp, f"{{{self.nsmap['cac']}}}Party")
        
        pid = etree.SubElement(party, f"{{{self.nsmap['cac']}}}PartyIdentification")
        self._add_cbc(pid, "ID", customer.id, schemeID=customer.id_scheme)
        
        ple = etree.SubElement(party, f"{{{self.nsmap['cac']}}}PartyLegalEntity")
        self._add_cbc(ple, "RegistrationName", customer.registration_name)
        
        reg_addr = etree.SubElement(ple, f"{{{self.nsmap['cac']}}}RegistrationAddress")
        addr_line = etree.SubElement(reg_addr, f"{{{self.nsmap['cac']}}}AddressLine")
        self._add_cbc(addr_line, "Line", customer.address_line)

    def _build_tax_total(self, parent, invoice):
        tt = etree.SubElement(parent, f"{{{self.nsmap['cac']}}}TaxTotal")
        self._add_cbc(tt, "TaxAmount", f"{invoice.tax_total_amount:.2f}", currencyID=invoice.currency_code)
        
        for sub in invoice.tax_subtotals:
            tst = etree.SubElement(tt, f"{{{self.nsmap['cac']}}}TaxSubtotal")
            self._add_cbc(tst, "TaxableAmount", f"{sub.taxable_amount:.2f}", currencyID=invoice.currency_code)
            self._add_cbc(tst, "TaxAmount", f"{sub.tax_amount:.2f}", currencyID=invoice.currency_code)
            
            tc = etree.SubElement(tst, f"{{{self.nsmap['cac']}}}TaxCategory")
            ts = etree.SubElement(tc, f"{{{self.nsmap['cac']}}}TaxScheme")
            self._add_cbc(ts, "ID", sub.tax_category_id)
            self._add_cbc(ts, "Name", sub.tax_category_name)
            self._add_cbc(ts, "TaxTypeCode", sub.tax_category_type_code)

    def _build_legal_monetary_total(self, parent, invoice):
        lmt = etree.SubElement(parent, f"{{{self.nsmap['cac']}}}LegalMonetaryTotal")
        self._add_cbc(lmt, "LineExtensionAmount", f"{invoice.legal_monetary_total_line_extension_amount:.2f}", currencyID=invoice.currency_code)
        self._add_cbc(lmt, "TaxInclusiveAmount", f"{invoice.legal_monetary_total_tax_inclusive_amount:.2f}", currencyID=invoice.currency_code)
        self._add_cbc(lmt, "PayableAmount", f"{invoice.legal_monetary_total_payable_amount:.2f}", currencyID=invoice.currency_code)

    def _build_invoice_line(self, parent, line):
        il = etree.SubElement(parent, f"{{{self.nsmap['cac']}}}InvoiceLine")
        self._add_cbc(il, "ID", line.id)
        self._add_cbc(il, "InvoicedQuantity", str(line.quantity), unitCode=line.unit_code)
        self._add_cbc(il, "LineExtensionAmount", f"{line.line_extension_amount:.2f}", currencyID="PEN")
        
        pr = etree.SubElement(il, f"{{{self.nsmap['cac']}}}PricingReference")
        acp = etree.SubElement(pr, f"{{{self.nsmap['cac']}}}AlternativeConditionPrice")
        self._add_cbc(acp, "PriceAmount", f"{line.price_amount:.2f}", currencyID="PEN")
        self._add_cbc(acp, "PriceTypeCode", line.price_type_code)
        
        tt = etree.SubElement(il, f"{{{self.nsmap['cac']}}}TaxTotal")
        self._add_cbc(tt, "TaxAmount", f"{line.tax_amount:.2f}", currencyID="PEN")
        tst = etree.SubElement(tt, f"{{{self.nsmap['cac']}}}TaxSubtotal")
        self._add_cbc(tst, "TaxableAmount", f"{line.taxable_amount:.2f}", currencyID="PEN")
        self._add_cbc(tst, "TaxAmount", f"{line.tax_amount:.2f}", currencyID="PEN")
        
        tc = etree.SubElement(tst, f"{{{self.nsmap['cac']}}}TaxCategory")
        self._add_cbc(tc, "Percent", str(line.tax_percent))
        self._add_cbc(tc, "TaxExemptionReasonCode", "10") # Hardcoded for now based on example
        ts = etree.SubElement(tc, f"{{{self.nsmap['cac']}}}TaxScheme")
        self._add_cbc(ts, "ID", "1000")
        self._add_cbc(ts, "Name", "IGV")
        self._add_cbc(ts, "TaxTypeCode", "VAT")
        
        item = etree.SubElement(il, f"{{{self.nsmap['cac']}}}Item")
        self._add_cbc(item, "Description", line.description)
        
        price = etree.SubElement(il, f"{{{self.nsmap['cac']}}}Price")
        self._add_cbc(price, "PriceAmount", f"{line.price_unit_amount:.10f}", currencyID="PEN")
