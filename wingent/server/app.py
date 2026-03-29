"""
FastAPI application entry point.

Run with:
    python -m wingent.server.app
"""

import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .state import app_state
from .routes.agents import router as agents_router
from .routes.tasks import router as tasks_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    yield
    # Shutdown: clean up executor if running
    if app_state.executor:
        await app_state.executor.shutdown()


app = FastAPI(title="Wingent", version="2.0", lifespan=lifespan)

# CORS for Vite dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# REST routes
app.include_router(agents_router)
app.include_router(tasks_router)


# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await app_state.ws_manager.connect(ws)
    try:
        while True:
            # Keep connection alive; client can send pings
            await ws.receive_text()
    except WebSocketDisconnect:
        app_state.ws_manager.disconnect(ws)


# Serve frontend static files in production
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "dist")
if os.path.isdir(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    uvicorn.run("wingent.server.app:app", host="0.0.0.0", port=8000, reload=True)
