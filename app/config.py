"""Application configuration."""
from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = "sqlite:///./propus_spool.db"
    
    # Spoolman
    spoolman_url: str = "http://localhost:7912"
    spoolman_api_key: str = ""
    
    # Feature Flags
    write_mode: bool = False
    push_remaining_to_spoolman: bool = True
    enable_klipper: bool = False
    
    # API Settings
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
