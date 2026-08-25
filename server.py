#!/usr/bin/env python3
import os
import json
import http.server
import firebase_admin
from firebase_admin import credentials, auth, firestore

# ============================================================
# LOAD FIREBASE CREDENTIALS
# ============================================================
cred_json = os.environ.get('FIREBASE_SERVICE_ACCOUNT_JSON')

if cred_json:
    try:
        cred_dict = json.loads(cred_json)
        cred = credentials.Certificate(cred_dict)
    except json.JSONDecodeError as e:
        print(f"❌ Error: FIREBASE_SERVICE_ACCOUNT_JSON is not valid JSON: {e}")
        raise
else:
    try:
        cred = credentials.Certificate("serviceAccountKey.json")
    except FileNotFoundError:
        print("❌ Error: serviceAccountKey.json not found and FIREBASE_SERVICE_ACCOUNT_JSON is not set.")
        raise

firebase_admin.initialize_app(cred)
db = firestore.client()
print("✅ Firebase Admin SDK initialized successfully.")

# ============================================================
# HTTP SERVER
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
            user = auth.create_user(
                email=email,
                password=password,
                display_name=name
            )
            uid = user.uid

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

            db.collection('users').document(uid).set(user_data)

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
            self.send_json_error(500, f"Server error: {str(e)}")

    def send_json_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({'success': False, 'error': message}).encode())

    def do_GET(self):
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'OK')
            return

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
    try:
        server = http.server.HTTPServer(('0.0.0.0', PORT), CustomHandler)
        print(f"✅ Server running on http://0.0.0.0:{PORT}")
        print(f"👉 POST /create-user endpoint ready.")
        print(f"👉 Health check at /health")
        server.serve_forever()
    except Exception as e:
        import sys
        print(f"❌ Server crashed: {e}", file=sys.stderr)
        raise