# app/config.py
import os
import json
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

class ConfigError(Exception):
    pass

@dataclass
class Config:
    ENV: str = os.getenv('ENVIRONMENT', 'development')
    
    # Secret names in Secret Manager
    SECRETS = {
        'notion': 'notion-secret',
        'drive_folder': 'drive-folder-id',
        'sa_key': 'service-account-key'  # For cases when not using workload identity
    }
    
    # Paths configuration remains the same
    BASE_DIR: Path = Path(__file__).parent.parent
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    TEMPLATE_CONFIG_PATH: Path = TEMPLATES_DIR / "templates_config.yaml"
    LOGS_DIR: Path = BASE_DIR / "logs"
    SECRETS_DIR: Path = BASE_DIR / "secrets"
    SA_PATH: Path = SECRETS_DIR / "service-account.json"
    
    # Initialize as None, will be set in post_init
    NOTION_SECRET: str = None
    DRIVE_FOLDER_ID: str = None
    
    DEBUG: bool = ENV == 'development'
    LOG_LEVEL: str = 'DEBUG' if DEBUG else 'INFO'

    def __post_init__(self):
        self._setup_directories()
        
        if self.ENV == 'development':
            self._load_development_config()
        else:
            self._load_production_config()
            
        self._validate_config()

    def _load_development_config(self):
        """Load configuration for development environment"""
        self.NOTION_SECRET = os.getenv('NOTION_SECRET')
        self.DRIVE_FOLDER_ID = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
        
        if not self.SA_PATH.exists():
            raise ConfigError(f"Service account file not found: {self.SA_PATH}")

    def _load_production_config(self):
        """Load configuration for production environment"""
        try:
            # Load all secrets from Secret Manager
            self.NOTION_SECRET = self._get_secret(self.SECRETS['notion'])
            self.DRIVE_FOLDER_ID = self._get_secret(self.SECRETS['drive_folder'])
            
            # Service account will be handled by workload identity by default
            self.USE_WORKLOAD_IDENTITY = os.getenv('USE_WORKLOAD_IDENTITY', 'true').lower() == 'true'
            
            if not self.USE_WORKLOAD_IDENTITY:
                # If not using workload identity, load SA from Secret Manager
                self._service_account_json = self._get_secret(self.SECRETS['sa_key'])
            
        except Exception as e:
            raise ConfigError(f"Failed to load production config: {str(e)}")

    def _get_secret(self, secret_id: str) -> str:
        from google.cloud import secretmanager
        
        project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
        if not project_id:
            raise ConfigError("GOOGLE_CLOUD_PROJECT is required in production")
        
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")

    def _validate_config(self):
        """Validate the configuration"""
        if not self.NOTION_SECRET:
            raise ConfigError("NOTION_SECRET is required")
        if not self.DRIVE_FOLDER_ID:
            raise ConfigError("DRIVE_FOLDER_ID is required")
        if not self.TEMPLATES_DIR.exists():
            raise ConfigError(f"Templates directory not found: {self.TEMPLATES_DIR}")
        if not self.TEMPLATE_CONFIG_PATH.exists():
            raise ConfigError(f"Template config not found: {self.TEMPLATE_CONFIG_PATH}")

    def _setup_directories(self):
        """Create necessary directories"""
        self.LOGS_DIR.mkdir(exist_ok=True)
        if self.ENV == 'development':
            self.SECRETS_DIR.mkdir(exist_ok=True)

    @property
    def service_account_info(self) -> dict:
        """Get service account credentials"""
        if self.ENV == 'production':
            if self.USE_WORKLOAD_IDENTITY:
                return {}  # Let Google client libraries handle auth
            return json.loads(self._service_account_json)
        return json.loads(self.SA_PATH.read_text())

config = Config()