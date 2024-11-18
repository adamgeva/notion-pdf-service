# app/config.py
import os
from pathlib import Path
from dataclasses import dataclass
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

@dataclass
class Config:
    """Application configuration"""
    
    # Environment
    ENV: str = os.getenv('ENVIRONMENT', 'development')
    
    # Paths
    BASE_DIR: Path = Path(__file__).parent.parent  # Points to project root
    TEMPLATES_DIR: Path = BASE_DIR / "templates"
    TEMPLATE_CONFIG_PATH: Path = TEMPLATES_DIR / "templates_config.yaml"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Service Account (for development)
    SECRETS_DIR: Path = BASE_DIR / "secrets"
    SA_PATH: Path = SECRETS_DIR / "service-account.json"
    
    # API Credentials
    NOTION_SECRET: str = os.getenv('NOTION_SECRET')
    DRIVE_FOLDER_ID: str = os.getenv('GOOGLE_DRIVE_FOLDER_ID')
    
    # Optional: Application settings
    DEBUG: bool = ENV == 'development'
    LOG_LEVEL: str = 'DEBUG' if DEBUG else 'INFO'
    
    def __post_init__(self):
        """Validate configuration after initialization"""
        self._validate_paths()
        self._validate_credentials()
        self._setup_directories()
        
        # In production, use Google Cloud Secret Manager
        if self.ENV == 'production':
            self._load_production_secrets()

    def _validate_paths(self):
        """Validate required paths exist"""
        if not self.TEMPLATES_DIR.exists():
            raise ConfigError(f"Templates directory not found: {self.TEMPLATES_DIR}")
            
        if not self.TEMPLATE_CONFIG_PATH.exists():
            raise ConfigError(f"Template config not found: {self.TEMPLATE_CONFIG_PATH}")
            
        if self.ENV == 'development' and not self.SA_PATH.exists():
            raise ConfigError(f"Service account file not found: {self.SA_PATH}")

    def _validate_credentials(self):
        """Validate required credentials are set"""
        if not self.NOTION_SECRET:
            raise ConfigError("NOTION_SECRET is required")
            
        if not self.DRIVE_FOLDER_ID:
            raise ConfigError("GOOGLE_DRIVE_FOLDER_ID is required")

    def _setup_directories(self):
        """Create necessary directories"""
        self.LOGS_DIR.mkdir(exist_ok=True)
        if self.ENV == 'development':
            self.SECRETS_DIR.mkdir(exist_ok=True)

    def _load_production_secrets(self):
        """Load secrets from Google Cloud Secret Manager in production"""
        try:
            if self.ENV == 'production':
                from google.cloud import secretmanager
                
                project_id = os.getenv('GOOGLE_CLOUD_PROJECT')
                if not project_id:
                    raise ConfigError("GOOGLE_CLOUD_PROJECT is required in production")
                
                client = secretmanager.SecretManagerServiceClient()
                
                def access_secret(secret_id: str) -> str:
                    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
                    response = client.access_secret_version(request={"name": name})
                    return response.payload.data.decode("UTF-8")
                
                # Load production secrets
                self.NOTION_SECRET = access_secret('notion-secret')
                # Service account credentials will be handled by workload identity
                
        except Exception as e:
            raise ConfigError(f"Failed to load production secrets: {str(e)}")

    @property
    def service_account_info(self) -> dict:
        """Get service account info based on environment"""
        if self.ENV == 'production':
            return {}  # Use default credentials in production
        else:
            import json
            with open(self.SA_PATH) as f:
                return json.load(f)

# Create global config instance
config = Config()

# Example usage:
if __name__ == "__main__":
    print(f"Environment: {config.ENV}")
    print(f"Templates Directory: {config.TEMPLATES_DIR}")
    print(f"Debug Mode: {config.DEBUG}")
    print(f"Log Level: {config.LOG_LEVEL}")