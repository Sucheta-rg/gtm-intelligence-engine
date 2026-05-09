import requests
import os
from dotenv import load_dotenv
load_dotenv()

key = os.environ.get("HUBSPOT_API_KEY")
r = requests.get(
    "https://api.hubapi.com/crm/v3/objects/companies",
    headers={"Authorization": f"Bearer {key}"},
    params={"properties": "name,key_materials", "limit": 3}
)
for c in r.json().get("results", []):
    p = c["properties"]
    print(p.get("name"), "|", p.get("key_materials"))