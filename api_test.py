import api_client
import json

# Test with a known RUC (e.g., SUNAT's RUC: 20131312955)
ruc = "20131312955"
print(f"Testing RUC: {ruc}")
result = api_client.get_person_data(ruc)
print(json.dumps(result, indent=4))
