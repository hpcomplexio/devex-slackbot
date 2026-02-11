#!/usr/bin/env python3
"""
Notion OAuth Setup Script

This script handles the OAuth flow for Notion authentication:
1. Reads NOTION_OAUTH_CLIENT_ID and NOTION_OAUTH_CLIENT_SECRET from .env
2. Creates a temporary HTTPS server for OAuth callback
3. Opens browser to Notion authorization page
4. Exchanges authorization code for access and refresh tokens
5. Outputs refresh token for storage in .env

Usage:
    python scripts/notion_oauth_setup.py

Prerequisites:
    - .env file with NOTION_OAUTH_CLIENT_ID and NOTION_OAUTH_CLIENT_SECRET
    - Notion OAuth integration created at https://www.notion.so/my-integrations
    - Redirect URI configured as https://localhost:8443/callback
"""

import http.server as h
import urllib.parse as p
import urllib.request as req
import webbrowser as w
import ssl
import tempfile
import subprocess
import os
import sys
import json
from pathlib import Path

# Configuration
PORT = 8443
REDIRECT_URI = f"https://localhost:{PORT}/callback"
NOTION_AUTH_URL = "https://api.notion.com/v1/oauth/authorize"
NOTION_TOKEN_URL = "https://api.notion.com/v1/oauth/token"

def load_env_vars():
    """Load CLIENT_ID and CLIENT_SECRET from .env file."""
    env_file = Path(__file__).parent.parent / ".env"

    if not env_file.exists():
        print("ERROR: .env file not found!")
        print(f"Expected location: {env_file}")
        sys.exit(1)

    client_id = None
    client_secret = None

    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line.startswith("NOTION_OAUTH_CLIENT_ID="):
                client_id = line.split("=", 1)[1].strip()
            elif line.startswith("NOTION_OAUTH_CLIENT_SECRET="):
                client_secret = line.split("=", 1)[1].strip()

    if not client_id or not client_secret:
        print("ERROR: Missing OAuth credentials in .env file!")
        print("Required variables:")
        print("  - NOTION_OAUTH_CLIENT_ID")
        print("  - NOTION_OAUTH_CLIENT_SECRET")
        print()
        print("Setup instructions:")
        print("1. Visit https://www.notion.so/my-integrations")
        print("2. Create new integration → OAuth type")
        print(f"3. Set redirect URI to {REDIRECT_URI}")
        print("4. Add Client ID and Secret to .env file")
        sys.exit(1)

    return client_id, client_secret

def create_ssl_cert():
    """Create self-signed SSL certificate for HTTPS server."""
    cert_dir = tempfile.mkdtemp()
    cert_file = f'{cert_dir}/cert.pem'
    key_file = f'{cert_dir}/key.pem'

    # Generate certificate
    subprocess.run(
        [
            'openssl', 'req', '-new', '-x509',
            '-keyout', key_file,
            '-out', cert_file,
            '-days', '1',
            '-nodes',
            '-subj', '/CN=localhost'
        ],
        stderr=subprocess.DEVNULL,
        check=True
    )

    return cert_file, key_file

def exchange_code_for_tokens(code, client_id, client_secret):
    """Exchange authorization code for access and refresh tokens."""
    # Prepare token exchange request
    data = json.dumps({
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI
    }).encode()

    # Notion requires Basic Auth with client_id:client_secret
    import base64
    credentials = f"{client_id}:{client_secret}"
    b64_credentials = base64.b64encode(credentials.encode()).decode()

    # Make request
    request = req.Request(
        NOTION_TOKEN_URL,
        data=data,
        method='POST',
        headers={
            'Authorization': f'Basic {b64_credentials}',
            'Content-Type': 'application/json'
        }
    )

    response = req.urlopen(request)
    result = json.loads(response.read().decode())

    return result

class OAuthHandler(h.BaseHTTPRequestHandler):
    """HTTP handler for OAuth callback."""

    client_id = None
    client_secret = None

    def log_message(self, *args):
        """Suppress HTTP server logs."""
        pass

    def do_GET(self):
        """Handle OAuth callback."""
        # Parse query parameters
        query = p.parse_qs(p.urlparse(self.path).query)
        code = query.get('code', [''])[0]
        error = query.get('error', [''])[0]

        if error:
            self._send_error(f"Authorization failed: {error}")
            return

        if not code:
            self._send_error("No authorization code received")
            return

        try:
            # Exchange code for tokens
            result = exchange_code_for_tokens(
                code,
                self.client_id,
                self.client_secret
            )

            if 'access_token' in result and 'refresh_token' in result:
                access_token = result['access_token']
                refresh_token = result['refresh_token']

                # Output tokens
                print("\n" + "="*70)
                print("SUCCESS! OAuth tokens obtained.")
                print("="*70)
                print()
                print("Add this to your .env file:")
                print()
                print(f"NOTION_OAUTH_REFRESH_TOKEN={refresh_token}")
                print()
                print("="*70)
                print()

                # Write refresh token to stdout for script capture
                sys.stdout.write(refresh_token + '\n')
                sys.stdout.flush()

                # Send success response to browser
                self._send_success()
            else:
                error_msg = result.get('error', 'Unknown error')
                self._send_error(f"Token exchange failed: {error_msg}")

        except Exception as e:
            self._send_error(f"Exception during token exchange: {str(e)}")

        # Exit after handling request
        os._exit(0)

    def _send_success(self):
        """Send success response to browser."""
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = """
        <html>
        <head>
            <title>Notion OAuth Success</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }
                h1 { color: #2eaadc; }
                .success { background-color: #d4edda; border: 1px solid #c3e6cb; padding: 15px; border-radius: 5px; }
            </style>
        </head>
        <body>
            <div class="success">
                <h1>✓ Success!</h1>
                <p>Notion OAuth tokens obtained successfully!</p>
                <p>Your refresh token has been displayed in the terminal.</p>
                <p>You can close this window and return to your terminal.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

    def _send_error(self, error_msg):
        """Send error response to browser."""
        print(f"\nERROR: {error_msg}", file=sys.stderr)
        self.send_response(500)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""
        <html>
        <head>
            <title>Notion OAuth Error</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #dc3545; }}
                .error {{ background-color: #f8d7da; border: 1px solid #f5c6cb; padding: 15px; border-radius: 5px; }}
            </style>
        </head>
        <body>
            <div class="error">
                <h1>✗ Error</h1>
                <p>{error_msg}</p>
                <p>Check your terminal for more details.</p>
            </div>
        </body>
        </html>
        """
        self.wfile.write(html.encode())

def main():
    """Run OAuth setup flow."""
    print("="*70)
    print("Notion OAuth Setup")
    print("="*70)
    print()

    # Load credentials from .env
    print("Loading OAuth credentials from .env...")
    client_id, client_secret = load_env_vars()
    print(f"✓ Client ID: {client_id[:20]}...")
    print()

    # Create SSL certificate
    print("Creating temporary SSL certificate...")
    cert_file, key_file = create_ssl_cert()
    print("✓ SSL certificate created")
    print()

    # Build authorization URL
    auth_url = f"{NOTION_AUTH_URL}?{p.urlencode({
        'client_id': client_id,
        'response_type': 'code',
        'owner': 'user',
        'redirect_uri': REDIRECT_URI
    })}"

    print("Opening browser for Notion authorization...")
    print(f"Authorization URL: {auth_url}")
    print()
    print("Steps:")
    print("1. Browser will open to Notion authorization page")
    print("2. Select the workspace to authorize")
    print("3. Click 'Select pages' to grant access to your FAQ page")
    print("4. Click 'Allow access'")
    print("5. Return to this terminal for your refresh token")
    print()

    # Open browser
    w.open(auth_url)

    print(f"Waiting for OAuth callback on https://localhost:{PORT}/callback...")
    print("(Press Ctrl+C to cancel)")
    print()

    # Set up handler with credentials
    OAuthHandler.client_id = client_id
    OAuthHandler.client_secret = client_secret

    # Create HTTPS server
    httpd = h.HTTPServer(('localhost', PORT), OAuthHandler)
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(cert_file, key_file)
    httpd.socket = context.wrap_socket(httpd.socket, server_side=True)

    # Serve until callback received
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nCancelled by user.")
        sys.exit(1)

if __name__ == "__main__":
    main()
