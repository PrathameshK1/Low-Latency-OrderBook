#!/usr/bin/env python3
"""
Simple HTTP server to serve the Order Book GUI
Runs on port 8080 by default
"""

import http.server
import socketserver
import os
import sys

PORT = 8080
DIRECTORY = "web/frontend"

class MyHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def end_headers(self):
        # Add CORS headers for WebSocket
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

def main():
    # Change to project root
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)
    os.chdir(project_root)
    
    if not os.path.exists(DIRECTORY):
        print(f"Error: Directory '{DIRECTORY}' not found!")
        print(f"Current directory: {os.getcwd()}")
        sys.exit(1)
    
    with socketserver.TCPServer(("", PORT), MyHTTPRequestHandler) as httpd:
        print(f"\\n{'='*60}")
        print(f"  📊 Order Book GUI Server")
        print(f"{'='*60}")
        print(f"  Serving at: http://localhost:{PORT}")
        print(f"  Directory: {os.path.abspath(DIRECTORY)}")
        print(f"  Press Ctrl+C to stop")
        print(f"{'='*60}\\n")
        
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\\n\\nServer stopped.")
            sys.exit(0)

if __name__ == "__main__":
    main()
