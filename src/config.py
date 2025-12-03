from pydantic import BaseModel
import os

class Settings(BaseModel):
    database_url: str = os.getenv("DATABASE_URL")
    tei_url: str = os.getenv("TEI_URL")
    tgi_url: str = os.getenv("TGI_URL")
    selenium_remote_url: str = os.getenv("SELENIUM_REMOTE_URL")

settings = Settings()