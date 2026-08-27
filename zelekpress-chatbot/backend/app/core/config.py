"""Configuración de la plataforma. Todo sale de variables de entorno
(nada de secretos en código). Ver .env.example."""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    APP_NAME: str = "Zelekpress Chatbots"
    APP_ENV: str = "development"          # development | production
    APP_URL: str = "http://localhost:5173"
    WIDGET_URL: str = "http://localhost:5173"

    # Base de datos. En dev, si no se define, cae a SQLite local para poder
    # arrancar sin Postgres (los embeddings/pgvector son de una fase posterior).
    DATABASE_URL: str = "sqlite:///./dev.db"
    REDIS_URL: str = "redis://localhost:6379/0"

    # Carpeta donde se guardan las imágenes subidas (launcher, logo, avatar).
    UPLOADS_DIR: str = "./uploads"

    # Seguridad
    JWT_SECRET: str = "cambiar-esto-en-produccion"
    JWT_ALG: str = "HS256"
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 14

    # Usuario Super Admin inicial (se crea con el seed)
    SUPERADMIN_EMAIL: str = "admin@zelekpress.com"
    SUPERADMIN_PASSWORD: str = "Zelekpress2026!"
    SUPERADMIN_NAME: str = "Zelekpress Admin"

    # Proveedores de IA
    AI_PROVIDER: str = "groq"                 # groq | (openai/anthropic/... en el futuro)
    DEFAULT_AI_MODEL: str = "llama-3.1-8b-instant"
    GROQ_API_KEY: str = ""
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    GEMINI_API_KEY: str = ""

    # CORS: orígenes permitidos para el frontend, separados por coma
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.DATABASE_URL.startswith("sqlite")


settings = Settings()
