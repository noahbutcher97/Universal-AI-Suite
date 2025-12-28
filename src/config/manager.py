import os
import json
import shutil
import keyring
from src.utils.logger import log

class ConfigManager:
    APP_NAME = "UniversalAISuite"
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".universal_ai_suite")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    
    DEFAULT_CONFIG = {
        "comfy_path": os.path.join(os.path.expanduser("~"), "ComfyUI"),
        "cli_scope": "user",
        "theme": "Dark",
        "first_run": True
    }

    SECURE_KEYS = ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GROK_API_KEY", "DEEPSEEK_API_KEY"]

    def __init__(self):
        self.config = self.load_config()

    def load_config(self):
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)
        
        if not os.path.exists(self.CONFIG_FILE):
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG.copy()
        
        try:
            with open(self.CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            log.error(f"Failed to load config: {e}. Loading defaults.")
            return self.DEFAULT_CONFIG.copy()

    def save_config(self, config=None):
        if config is None:
            config = self.config
        
        # Rollback mechanism: Backup existing config
        if os.path.exists(self.CONFIG_FILE):
            try:
                shutil.copy2(self.CONFIG_FILE, self.CONFIG_FILE + ".bak")
            except Exception as e:
                log.warning(f"Failed to backup config: {e}")

        try:
            with open(self.CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            log.error(f"Failed to save config: {e}")

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def get_secure(self, key):
        """Retrieve a sensitive value from OS keyring."""
        try:
            val = keyring.get_password(self.APP_NAME, key)
            return val if val else ""
        except Exception as e:
            # Handle keyring errors (No backend, locked, etc)
            log.error(f"Keyring get error for {key}: {e}")
            return ""

    def set_secure(self, key, value):
        """Save a sensitive value to OS keyring."""
        try:
            if value:
                keyring.set_password(self.APP_NAME, key, value)
            else:
                # If clearing, try to delete
                try:
                    keyring.delete_password(self.APP_NAME, key)
                except: pass
        except Exception as e:
            # Handle keyring errors
            log.error(f"Keyring set error for {key}: {e}")

    def migrate_legacy_keys(self):
        """Migrate keys from old config.json to Keyring."""
        if "api_keys" in self.config:
            log.info("Migrating legacy API keys to secure storage...")
            for k, v in self.config["api_keys"].items():
                if v:
                    self.set_secure(k, v)
            del self.config["api_keys"]
            self.save_config()

    def validate_config(self):
        """Ensure config structure is valid."""
        changes = False
        
        # Check required keys
        for key, default_val in self.DEFAULT_CONFIG.items():
            if key not in self.config:
                self.config[key] = default_val
                changes = True
        
        # Check types
        if not isinstance(self.config.get("comfy_path"), str):
            self.config["comfy_path"] = self.DEFAULT_CONFIG["comfy_path"]
            changes = True
            
        if changes:
            log.info("Config repaired with default values.")
            self.save_config()

    def get_resources(self):
        """Loads resource maps (CLI, Models)."""
        res_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources.json")
        if os.path.exists(res_file):
            try:
                with open(res_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                log.error(f"Failed to load resources: {e}")
        return {}

config_manager = ConfigManager()
config_manager.validate_config()
