"""
app/main.py
-----------
This is the ENTRY POINT of the FastAPI application.

Uvicorn command:
uvicorn app.main:app

Means:
- module: app.main
- object: app
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

# Import configuration
from app.settings import settings

# Import router module
from app.routers import startup, auth
from app.routers import profile
from app.routers import flight_search
from app.routers import llm_assist


# Create FastAPI application instance
app = FastAPI(
    title=settings.APP_NAME,   # Appears in OpenAPI docs
    version="1.0"
)

# Mount static folder
# URL /static/... → files inside app/static/
app.mount(
    "/static",
    StaticFiles(directory="app/static"),
    name="static"
)

# Attach router
# All routes defined in startup.router become active
app.include_router(startup.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(flight_search.router)
app.include_router(llm_assist.router)