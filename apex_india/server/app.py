"""
APEX INDIA — Project Server (FastAPI)
=====================================
Central API server that bridges the trading scheduler to the 
premium "Command Center" frontend.

Features:
- REST API for live P&L, positions, and signals.
- WebSocket for low-latency status updates.
- Remote control for trading modes (Paper/Real) and system halt.
"""

import os
import sys
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add project root to path
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from apex_india.utils.logger import get_logger

logger = get_logger("server")

app = FastAPI(title="APEX INDIA Command Center")

# Static files for the "Perfect" Frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

# CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ═══════════════════════════════════════════════════════════════
# MODELS
# ═══════════════════════════════════════════════════════════════

class SystemState(BaseModel):
    mode: str = "paper"
    running: bool = False
    market_open: bool = False
    equity: float = 1000000.0
    day_pnl: float = 0.0
    active_trades: int = 0
    circuit_breaker: str = "NORMAL"

# ═══════════════════════════════════════════════════════════════
# STATE MANAGEMENT (Global state shared with scheduler)
# ═══════════════════════════════════════════════════════════════

class StateStore:
    def __init__(self):
        self.state = {
            "mode": "paper",
            "running": False,
            "market_open": False,
            "equity": 10000.0,  # Starting small as per user request
            "day_pnl": 0.0,
            "pnl_pct": 0.0,
            "positions": [],
            "signals": [],
            "activity": [],
            "circuit_breaker": "NORMAL",
            "last_update": datetime.now().isoformat()
        }
        self.clients: List[WebSocket] = []

    def update(self, data: Dict):
        self.state.update(data)
        self.state["last_update"] = datetime.now().isoformat()

    async def broadcast(self):
        for client in self.clients:
            try:
                await client.send_json(self.state)
            except Exception:
                self.clients.remove(client)

store = StateStore()

# ═══════════════════════════════════════════════════════════════
# ENDPOINTS
# ═══════════════════════════════════════════════════════════════

@app.get("/api/state")
async def get_state():
    return store.state

@app.post("/api/mode")
async def toggle_mode(mode: str):
    if mode in ["paper", "real"]:
        store.update({"mode": mode})
        logger.info(f"System mode switched to: {mode.upper()}")
        return {"status": "success", "mode": mode}
    return {"status": "error", "message": "Invalid mode"}

@app.post("/api/halt")
async def halt_system():
    store.update({"running": False})
    logger.warning("SYSTEM HALT COMMAND RECEIVED VIA API")
    return {"status": "halted"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    store.clients.append(websocket)
    try:
        # Send initial state
        await websocket.send_json(store.state)
        while True:
            # Keep alive and wait for client messages if any
            await websocket.receive_text()
    except WebSocketDisconnect:
        store.clients.remove(websocket)
    except Exception:
        if websocket in store.clients:
            store.clients.remove(websocket)

# Mount static files last
app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
