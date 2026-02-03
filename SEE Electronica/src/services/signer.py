import xmlsec
from lxml import etree

class XMLSigner:
    def __init__(self):
        self.nsmap = {
            "ds": "http://www.w3.org/2000/09/xmldsig#",
            "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
            "ext": "urn:oasis:names:specification:ubl:schema:xsd:CommonExtensionComponents-2"
        }

    def sign(self, xml_content: bytes, key_path: str, cert_path: str, password: str = None) -> bytes:
        """
        Signs the XML content using XAdES-BES (Enveloped Signature).
        """
        root = etree.fromstring(xml_content)
        
        # Find the placeholder for the signature
        # In UBL 2.1, it's usually in ext:UBLExtensions/ext:UBLExtension/ext:ExtensionContent
        # We need to create the Signature node structure if it doesn't exist or find it
        
        # NOTE: The XMLBuilder already creates the structure:
        # <ext:UBLExtensions>
        #   <ext:UBLExtension>
        #     <ext:ExtensionContent>
        #       (Signature goes here)
        
        extension_content = root.find(".//ext:ExtensionContent", namespaces=self.nsmap)
        if extension_content is None:
            raise ValueError("Could not find ExtensionContent to place signature")

        # Create the Signature Node
        signature_node = xmlsec.template.create(
            root, 
            xmlsec.Transform.EXCL_C14N, 
            xmlsec.Transform.RSA_SHA1,
            ns="ds"
        )
        
        # Add the signature to the extension content
        extension_content.append(signature_node)
        
        # Add Reference
        ref = xmlsec.template.add_reference(
            signature_node, 
            xmlsec.Transform.SHA1, 
            uri=""
        )
        
        # Add Transforms
        xmlsec.template.add_transform(ref, xmlsec.Transform.ENVELOPED)
        
        # Add KeyInfo
        key_info = xmlsec.template.ensure_key_info(signature_node)
        xmlsec.template.add_x509_data(key_info)
        
        # Load Key
        ctx = xmlsec.SignatureContext()
        key = xmlsec.Key.from_file(key_path, xmlsec.KeyFormat.PEM, password)
        key.load_cert_from_file(cert_path, xmlsec.KeyFormat.PEM)
        
        ctx.key = key
        
        # Sign
        ctx.sign(signature_node)
        
        return etree.tostring(root, pretty_print=True, xml_declaration=True, encoding="utf-8")
