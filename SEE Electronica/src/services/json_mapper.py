from datetime import datetime
from src.models.invoice import Invoice, Party, InvoiceLine, TaxSubtotal

class JsonInvoiceMapper:
    @staticmethod
    def map(json_data: dict) -> Invoice:
        body = json_data.get("documentBody", {})
        
        # Helper to get text value safely
        def get_text(obj, key, default=""):
            if key in obj:
                item = obj[key]
                if isinstance(item, dict):
                    return item.get("_text", default)
                elif isinstance(item, list) and len(item) > 0:
                     return item[0].get("_text", default)
            return default

        # Helper to get attribute safely
        def get_attr(obj, key, attr_name, default=""):
            if key in obj:
                item = obj[key]
                if isinstance(item, dict):
                    return item.get("_attributes", {}).get(attr_name, default)
                elif isinstance(item, list) and len(item) > 0:
                    return item[0].get("_attributes", {}).get(attr_name, default)
            return default

        # 1. Basic Info
        invoice = Invoice()
        invoice.ubl_version = get_text(body, "cbc:UBLVersionID", "2.1")
        invoice.customization_id = get_text(body, "cbc:CustomizationID", "2.0")
        invoice.id = get_text(body, "cbc:ID")
        
        issue_date_str = get_text(body, "cbc:IssueDate")
        if issue_date_str:
            invoice.issue_date = datetime.strptime(issue_date_str, "%Y-%m-%d").date()
            
        issue_time_str = get_text(body, "cbc:IssueTime")
        if issue_time_str:
            try:
                invoice.issue_time = datetime.strptime(issue_time_str, "%H:%M:%S").time()
            except ValueError:
                pass # Keep default or handle error

        invoice.invoice_type_code = get_text(body, "cbc:InvoiceTypeCode")
        invoice.currency_code = get_text(body, "cbc:DocumentCurrencyCode")
        
        # Notes
        notes = body.get("cbc:Note")
        if isinstance(notes, list):
            invoice.note = notes[0].get("_text", "")
        elif isinstance(notes, dict):
            invoice.note = notes.get("_text", "")

        # 2. Supplier
        supplier_data = body.get("cac:AccountingSupplierParty", {}).get("cac:Party", {})
        supplier_id_node = supplier_data.get("cac:PartyIdentification", {}).get("cbc:ID", {})
        supplier_addr = supplier_data.get("cac:PartyLegalEntity", {}).get("cac:RegistrationAddress", {})
        
        invoice.supplier = Party(
            id=supplier_id_node.get("_text", ""),
            id_scheme=supplier_id_node.get("_attributes", {}).get("schemeID", "6"),
            registration_name=get_text(supplier_data.get("cac:PartyLegalEntity", {}), "cbc:RegistrationName"),
            address_line=get_text(supplier_addr.get("cac:AddressLine", {}), "cbc:Line"),
            address_type_code=get_text(supplier_addr, "cbc:AddressTypeCode")
        )

        # 3. Customer
        customer_data = body.get("cac:AccountingCustomerParty", {}).get("cac:Party", {})
        customer_id_node = customer_data.get("cac:PartyIdentification", {}).get("cbc:ID", {})
        
        invoice.customer = Party(
            id=customer_id_node.get("_text", ""),
            id_scheme=customer_id_node.get("_attributes", {}).get("schemeID", "6"),
            registration_name=get_text(customer_data.get("cac:PartyLegalEntity", {}), "cbc:RegistrationName"),
            address_line="" # Not always present for customer
        )

        # 4. Tax Total
        tax_total_node = body.get("cac:TaxTotal", {})
        invoice.tax_total_amount = float(get_text(tax_total_node, "cbc:TaxAmount", "0.0"))
        
        tax_subtotals = tax_total_node.get("cac:TaxSubtotal", [])
        if isinstance(tax_subtotals, dict):
            tax_subtotals = [tax_subtotals]
            
        for sub in tax_subtotals:
            tax_scheme = sub.get("cac:TaxCategory", {}).get("cac:TaxScheme", {})
            invoice.tax_subtotals.append(TaxSubtotal(
                taxable_amount=float(get_text(sub, "cbc:TaxableAmount", "0.0")),
                tax_amount=float(get_text(sub, "cbc:TaxAmount", "0.0")),
                tax_category_percent=18.0, # Usually inferred or hardcoded if not in JSON
                tax_category_id=get_text(tax_scheme, "cbc:ID", "1000"),
                tax_category_name=get_text(tax_scheme, "cbc:Name", "IGV"),
                tax_category_type_code=get_text(tax_scheme, "cbc:TaxTypeCode", "VAT")
            ))

        # 5. Legal Monetary Total
        lmt = body.get("cac:LegalMonetaryTotal", {})
        invoice.legal_monetary_total_line_extension_amount = float(get_text(lmt, "cbc:LineExtensionAmount", "0.0"))
        invoice.legal_monetary_total_tax_inclusive_amount = float(get_text(lmt, "cbc:TaxInclusiveAmount", "0.0"))
        invoice.legal_monetary_total_payable_amount = float(get_text(lmt, "cbc:PayableAmount", "0.0"))

        # 6. Invoice Lines
        lines = body.get("cac:InvoiceLine", [])
        if isinstance(lines, dict):
            lines = [lines]
            
        for line in lines:
            pricing_ref = line.get("cac:PricingReference", {}).get("cac:AlternativeConditionPrice", {})
            tax_total = line.get("cac:TaxTotal", {})
            tax_subtotal = tax_total.get("cac:TaxSubtotal", {})
            if isinstance(tax_subtotal, list): tax_subtotal = tax_subtotal[0] # Take first if list
            
            tax_category = tax_subtotal.get("cac:TaxCategory", {})
            
            inv_line = InvoiceLine(
                id=get_text(line, "cbc:ID"),
                quantity=float(get_text(line, "cbc:InvoicedQuantity", "0.0")),
                unit_code=get_attr(line, "cbc:InvoicedQuantity", "unitCode", "NIU"),
                line_extension_amount=float(get_text(line, "cbc:LineExtensionAmount", "0.0")),
                price_amount=float(get_text(pricing_ref, "cbc:PriceAmount", "0.0")),
                price_type_code=get_text(pricing_ref, "cbc:PriceTypeCode", "01"),
                description=get_text(line.get("cac:Item", {}), "cbc:Description"),
                tax_amount=float(get_text(tax_total, "cbc:TaxAmount", "0.0")),
                taxable_amount=float(get_text(tax_subtotal, "cbc:TaxableAmount", "0.0")),
                tax_percent=float(get_text(tax_category, "cbc:Percent", "18.0")),
                price_unit_amount=float(get_text(line.get("cac:Price", {}), "cbc:PriceAmount", "0.0"))
            )
            invoice.lines.append(inv_line)
            
        return invoice
