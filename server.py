import os
import json
import firebase_admin
from firebase_admin import credentials

# Try to get the credentials from the environment variable first
cred_json = os.environ.get('GOOGLE_APPLICATION_CREDENTIALS_JSON')

if cred_json:
    # If the environment variable exists, use it
    cred_dict = json.loads(cred_json)
    cred = credentials.Certificate(cred_dict)
else:
    # Fallback to the local file (for development)
    cred = credentials.Certificate("serviceAccountKey.json")

firebase_admin.initialize_app(cred)