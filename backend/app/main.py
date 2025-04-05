from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import logging
from typing import List
import os
import sys

# Import the path setup module first
from app.core.imports import APP_DIR, BACKEND_DIR

# Initialize logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Wolf - Retro AI Stockbroker")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development. In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# WebSocket connection manager - defined before importing endpoints to avoid circular imports
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_json(message)
            
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        await websocket.send_json(message)

# Create manager instance before importing endpoints
manager = ConnectionManager()

# Now import the endpoint modules (after manager is defined)
from app.api.endpoints import trades, users, calls

@app.get("/")
async def root():
    return {"message": "Welcome to Wolf - The Retro AI Stockbroker API"}

@app.websocket("/ws/{client_id}")
async def websocket_endpoint(websocket: WebSocket, client_id: str):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            # Process the received data
            logger.info(f"Received message from {client_id}: {data}")
            
            # Echo back for now, will be replaced with actual logic
            await manager.send_personal_message(
                {"status": "received", "data": data},
                websocket
            )
    except WebSocketDisconnect:
        manager.disconnect(websocket)
        logger.info(f"Client {client_id} disconnected")

# Include API routers
app.include_router(users.router)
app.include_router(trades.router)
app.include_router(calls.router)

if __name__ == "__main__":
    # If running this file directly
    print("Starting Wolf backend directly from app/main.py...")
    print(f"Python path includes: {BACKEND_DIR} and {APP_DIR}")
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True) 