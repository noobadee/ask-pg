from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    HUGGING_FACE_ACCESS_TOKEN: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


settings = Settings()
