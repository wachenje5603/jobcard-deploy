import os
import json
import firebase_admin
from firebase_admin import credentials

# --- Load Firebase credentials ---
cred_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')

if cred_json:
    # On Render: load from the environment variable
    try:
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    except json.JSONDecodeError as e:
        print(f"❌ Error: FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
        raise
else:
    # Locally: load from the file
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
    except FileNotFoundError:
        print("❌ Error: serviceAccountKey.json not found and FIREBASE_SERVICE_ACCOUNT_JSON is not set.")
        raise

firebase_admin.initialize_app(cred)
print("✅ Firebase Admin SDK initialized successfully.")