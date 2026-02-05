import http.server
import socketserver
import webbrowser
import urllib.parse
import threading
import requests
import time
import secrets
from datetime import datetime, timedelta
from typing import Optional, Callable, Dict
from src.utils.logger import log
from src.config.manager import config_manager

class AgentAuthService:
    """
    Manages local API authentication using Bearer Tokens.
    Ensures secure cross-process communication between Desktop Agent and Mobile/Web.
    """
    
    TOKEN_EXPIRY_DAYS = 7
    
    def __init__(self):
        self._active_tokens: Dict[str, datetime] = {}
        self._load_persisted_tokens()

    def generate_agent_token(self, label: str = "default_agent") -> str:
        """
        Generate a new secure Bearer token.
        """
        token = f"as_{secrets.token_urlsafe(32)}"
        expiry = datetime.utcnow() + timedelta(days=self.TOKEN_EXPIRY_DAYS)
        
        self._active_tokens[token] = expiry
        self._persist_token(token, expiry, label)
        
        log.info(f"Generated new API token for: {label}")
        return token

    def verify_token(self, token: str) -> bool:
        """
        Verify if a token is valid and not expired.
        """
        if not token:
            return False
            
        expiry = self._active_tokens.get(token)
        if not expiry:
            return False
            
        if datetime.utcnow() > expiry:
            # Token expired
            del self._active_tokens[token]
            self._remove_persisted_token(token)
            return False
            
        return True

    def _load_persisted_tokens(self):
        """Load tokens from secure config manager."""
        persisted = config_manager.get("auth.api_tokens", {})
        for token, data in persisted.items():
            try:
                expiry = datetime.fromisoformat(data["expiry"])
                if datetime.utcnow() < expiry:
                    self._active_tokens[token] = expiry
            except (ValueError, KeyError, TypeError):
                continue

    def _persist_token(self, token: str, expiry: datetime, label: str):
        """Store token metadata in config."""
        tokens = config_manager.get("auth.api_tokens", {})
        tokens[token] = {
            "expiry": expiry.isoformat(),
            "label": label,
            "created_at": datetime.utcnow().isoformat()
        }
        config_manager.set("auth.api_tokens", tokens)

    def _remove_persisted_token(self, token: str):
        """Remove token from config."""
        tokens = config_manager.get("auth.api_tokens", {})
        if token in tokens:
            del tokens[token]
            config_manager.set("auth.api_tokens", tokens)


# Hugging Face OAuth Endpoints
HF_AUTH_URL = "https://huggingface.co/oauth/authorize"
HF_TOKEN_URL = "https://huggingface.co/oauth/token"

class OAuthCallbackHandler(http.server.SimpleHTTPRequestHandler):
    """
    Handles the redirect callback from Hugging Face.
    Captures the 'code' parameter.
    """
    def do_GET(self):
        parsed_url = urllib.parse.urlparse(self.path)
        query = urllib.parse.parse_qs(parsed_url.query)
        
        if "code" in query:
            self.server.auth_code = query["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authentication Successful!</h1><p>You can close this window and return to the application.</p>")
        else:
            self.send_response(400)
            self.wfile.write(b"<h1>Authentication Failed</h1><p>No code received.</p>")

    def log_message(self, format, *args):
        pass  # Silence server logs

class AuthService:
    """
    Manages OAuth2 authentication flow for Hugging Face.
    """
    
    # -------------------------------------------------------------------------
    # DEVELOPER CONFIGURATION
    # Register your app at: https://huggingface.co/settings/applications/new
    # -------------------------------------------------------------------------
    HF_CLIENT_ID = "e42c299f-9d53-46c8-8bf8-03cfe6cdc9a6"
    HF_CLIENT_SECRET = "oauth_app_secret_bodgdLusxlQpsJRQVIsBryRJvviGOqQGKc" 
    
    REDIRECT_PORT = 10999
    REDIRECT_URI = f"http://localhost:{REDIRECT_PORT}/callback"

    # Provider Registry: Maps config keys to Auth URLs and Labels
    # For HF, we use Fine-grained with pre-filled permissions for maximum UX + Security.
    # Permissions: Read access to models (repo.content.read)
    _HF_PERMISSIONS = urllib.parse.quote('{"repo.content.read":true}')
    
    PROVIDER_MAP = {
        "HF_TOKEN": {
            "label": "Hugging Face",
            "url": f"https://huggingface.co/settings/tokens/new?tokenType=fineGrained&name=AI-Universal-Suite&permissions={_HF_PERMISSIONS}",
            "oauth": True,
            "pattern": r"^hf_[a-zA-Z0-9]{30,}$"
        },
        "OPENAI_API_KEY": {
            "label": "OpenAI",
            "url": "https://platform.openai.com/api-keys",
            "oauth": False,
            "pattern": r"^sk-[a-zA-Z0-9\-_]{20,}$"
        },
        "ANTHROPIC_API_KEY": {
            "label": "Anthropic",
            "url": "https://console.anthropic.com/settings/keys",
            "oauth": False,
            "pattern": r"^sk-ant-[a-zA-Z0-9\-_]{20,}$"
        },
        "GEMINI_API_KEY": {
            "label": "Google Gemini",
            "url": "https://aistudio.google.com/app/apikey",
            "oauth": False,
            "pattern": r"^AIza[0-9A-Za-z\-_]{35}$"
        },
        "GROK_API_KEY": {
            "label": "xAI (Grok)",
            "url": "https://console.x.ai/",
            "oauth": False,
            "pattern": r"^xai-[a-zA-Z0-9\-_]{10,}$"
        },
        "DEEPSEEK_API_KEY": {
            "label": "DeepSeek",
            "url": "https://platform.deepseek.com/api_keys",
            "oauth": False,
            "pattern": r"^sk-[a-zA-Z0-9]{30,}$"
        },
        "CIVITAI_API_KEY": {
            "label": "CivitAI",
            "url": "https://civitai.com/user/settings",
            "oauth": False,
            "pattern": r"^[a-f0-9]{32,}$" 
        },
        "COMFYUI_MANAGER_TOKEN": {
            "label": "ComfyUI Manager",
            "url": "https://github.com/ltdrdata/ComfyUI-Manager",
            "oauth": False
        }
    }

    def __init__(self):
        self.server = None
        self.server_thread = None

    def get_provider_info(self, key_name: str) -> dict:
        """Get metadata for a specific provider key."""
        return self.PROVIDER_MAP.get(key_name, {"label": key_name, "url": "", "oauth": False})

    def initiate_auth(self, key_name: str, on_success: Callable[[str], None], on_error: Callable[[str], None]) -> str:
        """
        Starts authentication or opens generation page.
        Returns: A status message to display to the user (e.g., instructions).
        """
        info = self.get_provider_info(key_name)
        
        # 1. Try OAuth (if supported and configured)
        if info["oauth"]:
            # Only use OAuth if developer has configured credentials
            if self.HF_CLIENT_ID and self.HF_CLIENT_ID != "YOUR_CLIENT_ID_HERE":
                self.start_oauth_flow(on_success, on_error)
                return "Check your browser to sign in."

        # 2. Fallback: Deep Link
        if info["url"]:
            webbrowser.open(info["url"])
            return f"Browser opened to {info['label']}.\nCreate a key and paste it here."
            
        return "No automated auth available for this provider."

    def start_oauth_flow(self, on_success: Callable[[str], None], on_error: Callable[[str], None]):
        """
        Starts the OAuth flow:
        1. Launches local server.
        2. Opens browser to HF Authorize page.
        3. Waits for callback.
        4. Exchanges code for token.
        """
        if self.HF_CLIENT_ID == "YOUR_CLIENT_ID_HERE":
            on_error("App not configured for OAuth. Developer must set HF_CLIENT_ID.")
            return

        try:
            # 1. Start Local Server
            self.server = socketserver.TCPServer(("localhost", self.REDIRECT_PORT), OAuthCallbackHandler)
            self.server.auth_code = None
            
            self.server_thread = threading.Thread(target=self.server.serve_forever)
            self.server_thread.daemon = True
            self.server_thread.start()
            
            # 2. Build Auth URL
            # Requesting expanded scopes for future capabilities
            params = {
                "client_id": self.HF_CLIENT_ID,
                "redirect_uri": self.REDIRECT_URI,
                "response_type": "code",
                "scope": "openid profile email read-repos contribute-repos write-repos manage-repos read-mcp write-discussions read-billing inference-api jobs webhooks",
                "state": "random_state_string" 
            }
            auth_url = f"{HF_AUTH_URL}?{urllib.parse.urlencode(params)}"
            
            # 3. Open Browser
            webbrowser.open(auth_url)
            
            # 4. Wait for Code (in background to not block UI)
            threading.Thread(target=self._wait_for_code, args=(on_success, on_error)).start()
            
        except Exception as e:
            self._shutdown_server()
            on_error(f"Failed to start auth flow: {str(e)}")

    def _wait_for_code(self, on_success, on_error):
        """Polls for auth code and performs token exchange."""
        timeout = 120 # 2 minutes timeout
        start = time.time()
        
        while time.time() - start < timeout:
            if hasattr(self.server, 'auth_code') and self.server.auth_code:
                # Code Received!
                self._exchange_token(self.server.auth_code, on_success, on_error)
                self._shutdown_server()
                return
            time.sleep(0.5)
            
        self._shutdown_server()
        on_error("Authentication timed out.")

    def _exchange_token(self, code: str, on_success, on_error):
        """Exchanges authorization code for access token."""
        if not self.HF_CLIENT_SECRET or self.HF_CLIENT_SECRET == "YOUR_CLIENT_SECRET_HERE":
            on_error("Developer must set HF_CLIENT_SECRET.")
            return

        payload = {
            "client_id": self.HF_CLIENT_ID,
            "client_secret": self.HF_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.REDIRECT_URI
        }
        
        try:
            response = requests.post(HF_TOKEN_URL, data=payload)
            if response.status_code == 200:
                data = response.json()
                token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                expires_in = data.get("expires_in")
                
                if token:
                    # Save persistence info
                    if refresh_token:
                        config_manager.set_secure("HF_REFRESH_TOKEN", refresh_token)
                    if expires_in:
                        config_manager.set("auth.hf_expires_at", time.time() + expires_in)
                        
                    on_success(token)
                else:
                    on_error("No access token in response.")
            else:
                on_error(f"Token exchange failed: {response.text}")
        except Exception as e:
            on_error(f"Network error during exchange: {str(e)}")

    def _shutdown_server(self):
        if self.server:
            self.server.shutdown()
            self.server.server_close()
            self.server = None

    def get_token_creation_url(self) -> str:
        """Fallback: Returns URL to manually create a token with pre-filled fields."""
        return "https://huggingface.co/settings/tokens/new?tokenType=read&name=AI-Universal-Suite"
