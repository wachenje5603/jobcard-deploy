#!/usr/bin/env python3
import http.server
import os

# CRITICAL FIX 1: Read PORT from environment (Render provides this)
PORT = int(os.environ.get('PORT', 8000))
INDEX_FILE = 'login.html'

class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        # CRITICAL FIX 2: Health check for Render
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
    server = http.server.HTTPServer(('0.0.0.0', PORT), CustomHandler)
    print(f"✅ Server running on http://0.0.0.0:{PORT}")
    print(f"👉 Root will serve {INDEX_FILE} (no directory listing).")
    print(f"👉 Health check available at /health")
    server.serve_forever()