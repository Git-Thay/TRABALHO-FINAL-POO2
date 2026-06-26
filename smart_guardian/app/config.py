"""Configurações centrais carregadas do .env (Singleton via lru_cache)."""
from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    twilio_account_sid: str = Field(default="", alias="TWILIO_ACCOUNT_SID")
    twilio_auth_token: str = Field(default="", alias="TWILIO_AUTH_TOKEN")
    twilio_whatsapp_from: str = Field(
        default="whatsapp:+14155238886", alias="TWILIO_WHATSAPP_FROM"
    )

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8000, alias="APP_PORT")

    yolo_model_path: str = Field(default="modelos/best.pt", alias="YOLO_MODEL_PATH")
    yolo_conf_threshold: float = Field(default=0.5, alias="YOLO_CONF_THRESHOLD")

    alerta_nivel_1_seg: int = Field(default=120, alias="ALERTA_NIVEL_1_SEG")
    alerta_nivel_2_seg: int = Field(default=300, alias="ALERTA_NIVEL_2_SEG")
    alerta_nivel_3_seg: int = Field(default=480, alias="ALERTA_NIVEL_3_SEG")

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
