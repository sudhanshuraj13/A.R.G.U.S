from app.main import app

if __name__ == "__main__":
    import uvicorn
    from app.core.config import settings

    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=False)
