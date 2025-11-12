"""Configuration management using Pydantic Settings."""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional


class Settings(BaseSettings):
    """Application settings."""
    
    # Database
    database_url: str = Field(
        default="postgresql://astropay:astropay@localhost:5432/activity_feed",
        env="DATABASE_URL"
    )
    
    # Redis
    redis_url: str = "redis://localhost:6379/0"
    
    # Elasticsearch
    elasticsearch_url: str = "http://localhost:9200"
    
    # Kafka
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_transactions_topic: str = "transactions"
    kafka_consumer_group: str = "transaction_indexer"
    kafka_auto_offset_reset: str = "earliest"  # earliest, latest, none
    kafka_enable_auto_commit: bool = False  # Manual commit for better control
    
    # Application
    debug: bool = True
    log_level: str = "INFO"
    api_prefix: str = "/api/v1"
    
    # Performance
    cache_ttl: int = 300  # 5 minutes
    page_size_default: int = 20
    page_size_max: int = 100
    
    # Resilience
    circuit_breaker_enabled: bool = False  # Set to False to disable circuit breakers
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_timeout: int = 60
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    
    # Rate Limiting
    rate_limit_enabled: bool = True
    rate_limit_default: int = 100  # requests per window
    rate_limit_window: int = 60  # seconds
    
    # Timeouts
    request_timeout: int = 30  # seconds
    external_service_timeout: int = 5  # seconds
    
    # Data Source
    use_elasticsearch_as_primary: bool = False  # If True, use Elasticsearch as primary data source
    
    # Authentication
    secret_key: str = "your-secret-key-change-in-production-use-env-variable"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 30
    require_auth: bool = False  # Set to True to require JWT for all endpoints
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

