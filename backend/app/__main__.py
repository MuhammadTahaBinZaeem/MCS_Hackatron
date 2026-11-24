import uvicorn
from app.config import Settings

if __name__ == "__main__":
    config = Settings()
    uvicorn.run("app.main:app", host=config.host, port=config.port, access_log=False)
