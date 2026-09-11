from fastapi import FastAPI

APP_NAME = "Boomi Builder API"
APP_VERSION = "0.1.0"


def create_app() -> FastAPI:
    application = FastAPI(
        title=APP_NAME,
        version=APP_VERSION,
    )

    @application.get("/health", tags=["system"])
    def health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "boomi-builder-api",
            "version": APP_VERSION,
        }

    return application


app = create_app()