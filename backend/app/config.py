from pathlib import Path

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "local"
    demo_mode: bool = True
    runtime_dir: Path = Path("runtime/demo")
    host: str = "127.0.0.1"
    port: int = Field(default=8000, ge=1, le=65535)
    allowed_student_email_domains: str = ""
    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str = ""
    smtp_password: str = Field(default="", repr=False)
    smtp_from: str = ""
    azure_enabled: bool = False
    azure_credential_file: Path = Path('security/api.env')
    azure_model_fast: str = 'gpt-5.4-nano'
    azure_model_standard: str = 'gpt-5.4-mini'
    azure_model_advanced: str = 'gpt-5.4'
    azure_model_escalation: str = 'gpt-5.6-luna'

    @field_validator("host")
    @classmethod
    def loopback_only(cls, value: str) -> str:
        if value != "127.0.0.1":
            raise ValueError("HOST must be 127.0.0.1")
        return value

    @model_validator(mode="after")
    def validate_runtime(self):
        path = self.runtime_dir.resolve()
        if path == Path(path.anchor) or path == Path.cwd().resolve():
            raise ValueError("RUNTIME_DIR must be a dedicated directory")
        if path.exists() and not path.is_dir():
            raise ValueError("RUNTIME_DIR must be a directory")
        self.runtime_dir = path
        return self
