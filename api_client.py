import http.client
import json
import traceback

def get_person_data(doc_number):
    """
    Obtiene datos de DNI o RUC usando la API de apisunat.com.
    Retorna un diccionario con los datos o None si hay error.
    """
    doc_number = str(doc_number).strip()
    
    if len(doc_number) == 8:
        endpoint = f"/dni/{doc_number}"
    elif len(doc_number) == 11:
        endpoint = f"/ruc/{doc_number}"
    else:
        return {"success": False, "message": "Longitud de documento inválida (debe ser 8 o 11 dígitos)."}

    try:
        conn = http.client.HTTPSConnection("dniruc.apisunat.com")
        boundary = ''
        payload = ''
        headers = {
            'Origin': 'https://apisunat.com',
            'Content-type': 'multipart/form-data; boundary={}'.format(boundary)
        }
        conn.request("GET", endpoint, payload, headers)
        res = conn.getresponse()
        data = res.read()
        decoded_data = data.decode("utf-8")
        
        json_data = json.loads(decoded_data)
        return json_data

    except Exception as e:
        print(f"Error en API SUNAT: {e}")
        traceback.print_exc()
        return {"success": False, "message": f"Error de conexión: {str(e)}"}