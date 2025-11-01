# [LEGACY ENTRYPOINT] Use the unified FastAPI app from app.main
from app.main import app

# Optional local run (uvicorn) for compatibility
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
