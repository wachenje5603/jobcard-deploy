#!/usr/bin/env python3
import http.server
import os
import json
import base64
import firebase_admin
from firebase_admin import credentials, auth, firestore

# ============================================================
# INIT FIREBASE ADMIN SDK
# ============================================================
# Option 1: Use environment variable (base64 encoded JSON)
SERVICE_ACCOUNT_B64 = os.environ.get('FIREBASE_SERVICE_ACCOUNT_B64')
if SERVICE_ACCOUNT_B64:
    # Decode from base64
    service_account_json = base64.b64decode(SERVICE_ACCOUNT_B64).decode('utf-8')
    cred = credentials.Certificate(json.loads(service_account_json))
else:
    # Fallback to file (for local testing)
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
    except FileNotFoundError:
        print("ERROR: No service account credentials found. Set FIREBASE_SERVICE_ACCOUNT_B64 env var.")
        raise

firebase_admin.initialize_app(cred)
db = firestore.client()
print("✅ Firebase Admin SDK initialized.")

# ============================================================
# PORT
# ============================================================
PORT = int(os.environ.get('PORT', 8000))
INDEX_FILE = 'login.html'

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        if self.path == '/create-user':
            self.handle_create_user()
        else:
            self.send_error(404, "Not found")

    def handle_create_user(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length)
        try:
            data = json.loads(body)
        except:
            self.send_json_error(400, "Invalid JSON")
            return

        # Required fields
        email = data.get('email')
        password = data.get('password')
        name = data.get('name')
        role = data.get('role', 'requester')
        department = data.get('department')
        departments = data.get('departments')
        whatsapp = data.get('whatsapp', '')

        if not email or not password or not name:
            self.send_json_error(400, "Missing required fields: email, password, name")
            return

        try:
            # 1. Create user in Firebase Auth
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            uid = user.uid

            # 2. Build Firestore user document
            user_data = {
                'name': name,
                'email': email,
                'role': role,
                'whatsapp': whatsapp,
                'approved': True,
                'createdAt': firestore.SERVER_TIMESTAMP,
                'updatedAt': firestore.SERVER_TIMESTAMP
            }

            if role == 'requester':
                user_data['department'] = department
                user_data['departments'] = None
            elif role == 'maintenance':
                user_data['departments'] = departments or []
                user_data['department'] = None
            else:  # admin
                user_data['department'] = None
                user_data['departments'] = None

            # 3. Write to Firestore
            db.collection('users').document(uid).set(user_data)

            # 4. Send success response
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({
                'success': True,
                'uid': uid,
                'message': f'User {name} created successfully.'
            }).encode())

        except auth.EmailAlreadyExistsError:
            self.send_json_error(400, "Email already in use.")
        except Exception as e:
            print("Error creating user:", str(e))
            self.send_json_error(500, f"Server error: {str(e)}")

    def send_json_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': False, 'error': message}).encode())

    def do_GET(self):
        # Health check
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            return

        # Serve static files
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            if self.path in ('/', '/index.html'):
                self.path = '/' + INDEX_FILE
                return super().do_GET()
            else:
                self.send_error(404, "Directory listing not allowed")
                return
        return super().do_GET()

    def list_directory(self, path):
        self.send_error(404, "Directory listing not allowed")
        return None

if __name__ == '__main__':
    server = http.server.HTTPServer(('0.0.0.0', PORT), CustomHandler)
    print(f"✅ Server running on http://0.0.0.0:{PORT}")
    print(f"👉 POST /create-user endpoint ready.")
    server.serve_forever()