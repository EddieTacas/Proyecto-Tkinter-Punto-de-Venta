import json
import os
from datetime import datetime, timedelta

class JSONGenerator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def generate_invoice_json(self, sale_data):
        """
        Generates a JSON file for the sale adhering to the UBL-ish structure.
        sale_data expected keys:
            - issuer: {ruc, name, address, ubl_version, customization_id}
            - customer: {doc_type, doc_number, name, address}
            - document: {type_name, series, number, issue_date (datetime), currency, total, items}
            - items: list of {description, quantity, price_unit_inc_igv, unit_code}
            - totals: {taxable, igv, total}
        """
        
        doc = sale_data['document']
        issuer = sale_data['issuer']
        customer = sale_data['customer']
        items = sale_data['items']
        
        # Determine Type Code
        type_name = doc['type_name'].upper()
        if "FACTURA" in type_name:
            invoice_type_code = "01"
            doc_prefix = "F001" if not doc['series'] else doc['series'] # fallback
        elif "BOLETA" in type_name:
            invoice_type_code = "03"
            doc_prefix = "B001" if not doc['series'] else doc['series']
        else:
            # Nota de Venta
            invoice_type_code = "80" # Generic internal code
            doc_prefix = "NV01" if not doc['series'] else doc['series']

        # Format Series-Number
        # Ensure number is padded to 8 digits if standard, or just use as is
        # Example filename: 20136564367-01-F001-00000009
        # Series: F001, Number: 9 -> 00000009
        try:
            number_padded = f"{int(doc['number']):08d}"
        except:
            number_padded = str(doc['number'])
            
        full_id = f"{doc_prefix}-{number_padded}"
        
        # Filename construction
        # {RUC}-{TYPE}-{SERIES}-{NUMBER}
        filename_base = f"{issuer['ruc']}-{invoice_type_code}-{full_id}"
        
        # Date/Time
        issue_date_str = doc['issue_date'].strftime("%Y-%m-%d")
        issue_time_str = doc['issue_date'].strftime("%H:%M:%S")
        
        # Calculations (Re-verify items)
        # Note: The input 'items' should ideally have pre-calculated values, 
        # but we can calculate here to ensure consistency with the JSON example format.
        
        invoice_lines = []
        total_taxable_accum = 0.0
        total_igv_accum = 0.0
        
        for idx, item in enumerate(items, 1):
            price_inc_igv = float(item['price_unit_inc_igv'])
            quantity = float(item['quantity'])
            
            # Base Unit Price (Value)
            # Price = Value * 1.18
            # Value = Price / 1.18
            price_base = price_inc_igv / 1.18
            
            # Line Extension Amount (Value * Qty)
            line_extension = price_base * quantity
            
            # IGV for Line
            igv_line = (price_base * 0.18) * quantity
            
            # Create Line Object
            line_obj = {
                "cbc:ID": { "_text": idx },
                "cbc:InvoicedQuantity": {
                    "_attributes": { "unitCode": item.get('unit_code', 'NIU') },
                    "_text": quantity
                },
                "cbc:LineExtensionAmount": {
                    "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                    "_text": round(line_extension, 2)
                },
                "cac:PricingReference": {
                    "cac:AlternativeConditionPrice": {
                        "cbc:PriceAmount": {
                            "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                            "_text": round(price_inc_igv, 2)
                        },
                        "cbc:PriceTypeCode": { "_text": "01" } # Precio Unitario (Incluye IGV)
                    }
                },
                "cac:TaxTotal": {
                    "cbc:TaxAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(igv_line, 2)
                    },
                    "cac:TaxSubtotal": [
                        {
                            "cbc:TaxableAmount": {
                                "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                                "_text": round(line_extension, 2)
                            },
                            "cbc:TaxAmount": {
                                "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                                "_text": round(igv_line, 2)
                            },
                            "cac:TaxCategory": {
                                "cbc:Percent": { "_text": 18 },
                                "cbc:TaxExemptionReasonCode": { "_text": "10" }, # Gravado - Operación Onerosa
                                "cac:TaxScheme": {
                                    "cbc:ID": { "_text": "1000" },
                                    "cbc:Name": { "_text": "IGV" },
                                    "cbc:TaxTypeCode": { "_text": "VAT" }
                                }
                            }
                        }
                    ]
                },
                "cac:Item": {
                    "cbc:Description": { "_text": item['description'] }
                },
                "cac:Price": {
                    "cbc:PriceAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(price_base, 10)
                    }
                }
            }
            invoice_lines.append(line_obj)
            total_taxable_accum += line_extension
            total_igv_accum += igv_line

        # Recalculate Totals to match (rounding might cause off-by-cent issues, standard is sum lines)
        total_taxable_rounded = round(total_taxable_accum, 2)
        total_igv_rounded = round(total_igv_accum, 2)
        total_payable = round(total_taxable_rounded + total_igv_rounded, 2)
        
        # Construct Main Body
        json_body = {
            "personaId": "6955d7ceba1b0d00151fa60d", 
            "personaToken": "DEV_U2PgAfc6lbZ5Bdoe0JFRNL6MTDsAUVTcarvmdDWT4q9CeuIE5O3EgH0fhz60oLdH",
            "fileName": filename_base,
            "documentBody": {
                "cbc:UBLVersionID": { "_text": "2.1" },
                "cbc:CustomizationID": { "_text": "2.0" },
                "cbc:ID": { "_text": full_id },
                "cbc:IssueDate": { "_text": issue_date_str },
                "cbc:IssueTime": { "_text": issue_time_str },
                "cbc:InvoiceTypeCode": {
                    "_attributes": { "listID": "0101" },
                    "_text": invoice_type_code
                },
                "cbc:Note": [
                    {
                        "_text": self._number_to_text(total_payable), 
                        "_attributes": { "languageLocaleID": "1000" }
                    }
                ],
                "cbc:DocumentCurrencyCode": { "_text": doc.get('currency', 'PEN') },
                "cac:AccountingSupplierParty": {
                    "cac:Party": {
                        "cac:PartyIdentification": {
                            "cbc:ID": {
                                "_attributes": { "schemeID": "6" }, # 6 = RUC
                                "_text": issuer['ruc']
                            }
                        },
                        "cac:PartyName": {
                            "cbc:Name": { "_text": issuer.get('commercial_name', '') if issuer.get('commercial_name', '') else issuer['name'] }
                        },
                        "cac:PartyLegalEntity": {
                            "cbc:RegistrationName": { "_text": issuer['name'] },
                            "cac:RegistrationAddress": {
                                "cbc:AddressTypeCode": { "_text": issuer.get('establishment_code', '0000') },
                                "cac:AddressLine": {
                                    "cbc:Line": { "_text": issuer['address'] }
                                }
                            }
                        }
                    }
                },
                "cac:AccountingCustomerParty": {
                    "cac:Party": {
                        "cac:PartyIdentification": {
                            "cbc:ID": {
                                "_attributes": { 
                                    "schemeID": "6" if len(customer.get('doc_number', '')) == 11 else "1" 
                                }, 
                                "_text": customer.get('doc_number', '') if customer.get('doc_number', '') else "00000000"
                            }
                        },
                        "cac:PartyLegalEntity": {
                            "cbc:RegistrationName": { "_text": "---" if customer.get('doc_number', '') == "00000000" or not customer.get('doc_number', '') else customer['name'] },
                            "cac:RegistrationAddress": {
                                "cac:AddressLine": {
                                    "cbc:Line": { "_text": customer['address'] if customer.get('address') else "-" }
                                }
                            }
                        }
                    }
                },
                "cac:TaxTotal": {
                    "cbc:TaxAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(total_igv_rounded, 2)
                    },
                    "cac:TaxSubtotal": [
                        {
                            "cbc:TaxableAmount": {
                                "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                                "_text": round(total_taxable_rounded, 2)
                            },
                            "cbc:TaxAmount": {
                                "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                                "_text": round(total_igv_rounded, 2)
                            },
                            "cac:TaxCategory": {
                                "cac:TaxScheme": {
                                    "cbc:ID": { "_text": "1000" },
                                    "cbc:Name": { "_text": "IGV" },
                                    "cbc:TaxTypeCode": { "_text": "VAT" }
                                }
                            }
                        }
                    ]
                },
                "cac:LegalMonetaryTotal": {
                    "cbc:LineExtensionAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(total_taxable_rounded, 2)
                    },
                    "cbc:TaxInclusiveAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(total_payable, 2)
                    },
                    "cbc:PayableAmount": {
                        "_attributes": { "currencyID": doc.get('currency', 'PEN') },
                        "_text": round(total_payable, 2)
                    }
                },
                "cac:PaymentTerms": [
                    {
                        "cbc:ID": { "_text": "FormaPago" },
                        "cbc:PaymentMeansID": { "_text": "Contado" }
                    }
                ],
                "cac:InvoiceLine": invoice_lines
            }
        }
        
        # Write File
        output_path = os.path.join(self.output_dir, f"{filename_base}.json")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(json_body, f, indent=4, ensure_ascii=False)
            
        return output_path

    def _number_to_text(self, amount):
        def num_to_text_int(n):
            if n == 0: return ""
            
            unidades = ["", "UN", "DOS", "TRES", "CUATRO", "CINCO", "SEIS", "SIETE", "OCHO", "NUEVE"]
            decenas = ["", "DIEZ", "VEINTE", "TREINTA", "CUARENTA", "CINCUENTA", "SESENTA", "SETENTA", "OCHENTA", "NOVENTA"]
            diez_y = ["DIEZ", "ONCE", "DOCE", "TRECE", "CATORCE", "QUINCE", "DIECISEIS", "DIECISIETE", "DIECIOCHO", "DIECINUEVE"]
            veinte_y = ["VEINTE", "VEINTIUNO", "VEINTIDOS", "VEINTITRES", "VEINTICUATRO", "VEINTICINCO", "VEINTISEIS", "VEINTISIETE", "VEINTIOCHO", "VEINTINUEVE"]
            centenas = ["", "CIENTO", "DOSCIENTOS", "TRESCIENTOS", "CUATROCIENTOS", "QUINIENTOS", "SEISCIENTOS", "SETECIENTOS", "OCHOCIENTOS", "NOVECIENTOS"]

            if n < 10:
                return unidades[n]
            elif n < 20:
                return diez_y[n - 10]
            elif n < 30:
                return veinte_y[n - 20]
            elif n < 100:
                u = n % 10
                if u == 0: return decenas[n // 10]
                return f"{decenas[n // 10]} Y {unidades[u]}"
            elif n < 1000:
                if n == 100: return "CIEN"
                return f"{centenas[n // 100]} {num_to_text_int(n % 100)}"
            elif n < 1000000:
                miles = n // 1000
                resto = n % 1000
                s_miles = "MIL"
                if miles > 1:
                    s_miles = f"{num_to_text_int(miles)} MIL"
                return f"{s_miles} {num_to_text_int(resto)}".strip()
            # Handle larger numbers if needed (millions)
            elif n < 1000000000:
                millones = n // 1000000
                resto = n % 1000000
                s_millones = "UN MILLON"
                if millones > 1:
                     s_millones = f"{num_to_text_int(millones)} MILLONES"
                return f"{s_millones} {num_to_text_int(resto)}".strip()
            
            return str(n)

        amount_int = int(amount)
        decimal_part = int(round((amount - amount_int) * 100))
        
        text_int = num_to_text_int(amount_int)
        if text_int == "": text_int = "CERO"
        
        return f"{text_int} CON {decimal_part:02d}/100 SOLES"
