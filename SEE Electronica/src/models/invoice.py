from dataclasses import dataclass, field
from typing import List, Optional
from datetime import date, time

@dataclass
class Party:
    id: str  # RUC/DNI
    id_scheme: str = "6"  # 6=RUC, 1=DNI
    name: str = ""
    registration_name: str = ""
    address_line: str = ""
    address_type_code: str = "0000"
    ubigeo: str = ""  # Not present in example but usually required
    country_code: str = "PE"
    
@dataclass
class TaxSubtotal:
    taxable_amount: float
    tax_amount: float
    tax_category_percent: float
    tax_category_id: str = "1000"
    tax_category_name: str = "IGV"
    tax_category_type_code: str = "VAT"
    tax_exemption_reason_code: str = "10" # 10=Gravado - Operación Onerosa

@dataclass
class InvoiceLine:
    id: str
    quantity: float
    unit_code: str
    line_extension_amount: float
    price_amount: float
    price_type_code: str = "01"
    description: str = ""
    tax_amount: float = 0.0
    taxable_amount: float = 0.0
    tax_percent: float = 18.0
    price_unit_amount: float = 0.0 # Price per unit including tax (optional/calculated)

@dataclass
class Invoice:
    ubl_version: str = "2.1"
    customization_id: str = "2.0"
    id: str = "" # SERIE-NUMERO
    issue_date: date = field(default_factory=date.today)
    issue_time: time = field(default_factory=lambda: time(0, 0, 0))
    invoice_type_code: str = "01" # 01=Factura, 03=Boleta
    note: str = ""
    currency_code: str = "PEN"
    
    supplier: Party = field(default_factory=lambda: Party(id=""))
    customer: Party = field(default_factory=lambda: Party(id=""))
    
    tax_total_amount: float = 0.0
    tax_subtotals: List[TaxSubtotal] = field(default_factory=list)
    
    legal_monetary_total_line_extension_amount: float = 0.0
    legal_monetary_total_tax_inclusive_amount: float = 0.0
    legal_monetary_total_payable_amount: float = 0.0
    
    lines: List[InvoiceLine] = field(default_factory=list)
