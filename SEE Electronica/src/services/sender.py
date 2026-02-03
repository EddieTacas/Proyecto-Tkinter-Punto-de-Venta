import zipfile
import io
import requests
import base64
import os
from dataclasses import dataclass

@dataclass
class ServiceResponse:
    success: bool
    message: str
    cdr_zip: bytes = None
    error_code: str = None

class SunatSender:
    def __init__(self, username, password, endpoint_url="https://e-beta.sunat.gob.pe/ol-ti-itcpfegem-beta/billService"):
        self.username = username
        self.password = password
        self.endpoint_url = endpoint_url

    def send_bill(self, filename: str, xml_content: bytes) -> ServiceResponse:
        # 1. Zip the XML
        zip_buffer = io.BytesIO()
        base_name = os.path.splitext(filename)[0]
        zip_filename = f"{base_name}.zip"
        
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
            zip_file.writestr(filename, xml_content)
        
        zip_content = zip_buffer.getvalue()
        zip_base64 = base64.b64encode(zip_content).decode('utf-8')
        
        # 2. Construct SOAP Envelope
        soap_envelope = f"""
        <soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:ser="http://service.sunat.gob.pe" xmlns:wsse="http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd">
            <soapenv:Header>
                <wsse:Security>
                    <wsse:UsernameToken>
                        <wsse:Username>{self.username}</wsse:Username>
                        <wsse:Password>{self.password}</wsse:Password>
                    </wsse:UsernameToken>
                </wsse:Security>
            </soapenv:Header>
            <soapenv:Body>
                <ser:sendBill>
                    <fileName>{zip_filename}</fileName>
                    <contentFile>{zip_base64}</contentFile>
                </ser:sendBill>
            </soapenv:Body>
        </soapenv:Envelope>
        """
        
        # 3. Send Request
        headers = {
            'Content-Type': 'text/xml;charset=UTF-8',
            'SOAPAction': 'urn:sendBill'
        }
        
        try:
            response = requests.post(self.endpoint_url, data=soap_envelope, headers=headers)
            
            if response.status_code != 200:
                return ServiceResponse(False, f"HTTP Error: {response.status_code}", error_code=str(response.status_code))
                
            # 4. Parse Response
            # Simple parsing to extract applicationResponse
            # In a real app, use lxml or a SOAP client to parse properly
            response_text = response.text
            if "applicationResponse" in response_text:
                start = response_text.find("<applicationResponse>") + len("<applicationResponse>")
                end = response_text.find("</applicationResponse>")
                cdr_base64 = response_text[start:end]
                cdr_zip = base64.b64decode(cdr_base64)
                return ServiceResponse(True, "Success", cdr_zip=cdr_zip)
            elif "faultstring" in response_text:
                 start = response_text.find("<faultstring>") + len("<faultstring>")
                 end = response_text.find("</faultstring>")
                 error_msg = response_text[start:end]
                 return ServiceResponse(False, f"SOAP Fault: {error_msg}")
            else:
                return ServiceResponse(False, "Unknown response format")
                
        except Exception as e:
            return ServiceResponse(False, str(e))
