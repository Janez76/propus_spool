"""
Configuration management for propus_spool application
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Database
    database_url: str = "sqlite:///./propus_spool.db"
    
    # Spoolman Integration
    spoolman_url: Optional[str] = None
    spoolman_api_key: Optional[str] = None
    
    # NFC Write Configuration
    write_mode: bool = False
    
    # Spoolman Sync
    push_remaining_to_spoolman: bool = True
    
    # Klipper Integration
    enable_klipper: bool = False
    klipper_moonraker_url: Optional[str] = None
    
    # Application Settings
    log_level: str = "INFO"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    
    # CORS Settings
    cors_origins: str = "*"
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False
    )
    
    @property
    def cors_origins_list(self) -> list[str]:
        """Parse CORS origins string into list"""
        if self.cors_origins == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",")]


# Global settings instance
settings = Settings()
