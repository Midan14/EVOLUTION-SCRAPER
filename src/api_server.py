#!/usr/bin/env python3
"""
API Server for Evolution Gaming Scraper
Exposes scraped baccarat results via REST API

Your main bot can consume this API to get real-time data
"""
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import uvicorn
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import config
from database import db

# ============== Lifespan ==============

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage startup and shutdown events"""
    # Startup
    await db.connect()
    yield
    # Shutdown
    await db.close()


# FastAPI app
app = FastAPI(
    title="Evolution Baccarat Scraper API",
    description="Real-time baccarat results from Evolution Gaming",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS - configurable via environment variable
_allowed_origins = os.getenv("CORS_ORIGINS", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)


# ============== Models ==============

class BaccaratResult(BaseModel):
    round_id: str
    timestamp: str
    result: str  # P, B, or T
    player_score: Optional[int] = None
    banker_score: Optional[int] = None
    player_cards: Optional[List[str]] = None
    banker_cards: Optional[List[str]] = None
    is_natural: bool = False
    lightning_cards: Optional[List[str]] = None
    multipliers: Optional[dict] = None
    table_id: Optional[str] = None


class Statistics(BaseModel):
    total_rounds: int
    player_wins: int
    banker_wins: int
    ties: int
    player_percentage: float
    banker_percentage: float
    tie_percentage: float
    avg_player_score: float
    avg_banker_score: float
    period_hours: int


class Streak(BaseModel):
    side: Optional[str] = None
    side_code: Optional[str] = None
    length: int


class HealthResponse(BaseModel):
    status: str
    database: str
    timestamp: str
    rounds_captured: int
    last_frame_at: Optional[str] = None


# ============== Endpoints ==============

@app.get("/", tags=["Health"])
async def root():
    """Root endpoint"""
    return {
        "name": "Evolution Baccarat Scraper API",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "ok",
        "database": "connected" if db._connection else "disconnected",
        "timestamp": datetime.utcnow().isoformat(),
        "rounds_captured": getattr(db, "rounds_captured", 0),
        "last_frame_at": getattr(db, "last_frame_at", None),
    }


@app.get("/api/results", response_model=List[BaccaratResult], tags=["Results"])
async def get_results(
    limit: int = Query(default=100, ge=1, le=1000, description="Number of results to return"),
    table_id: Optional[str] = Query(default=None, description="Filter by table ID"),
):
    """
    Get recent baccarat results

    - **limit**: Number of results (1-1000)
    - **table_id**: Optional filter by table
    """
    results = await db.get_recent_results(limit)

    if table_id:
        results = [r for r in results if r.get("table_id") == table_id]

    return results


@app.get("/api/results/latest", response_model=Optional[BaccaratResult], tags=["Results"])
async def get_latest_result():
    """Get the most recent result"""
    results = await db.get_recent_results(1)
    if not results:
        return None
    return results[0]


@app.get("/api/results/history", tags=["Results"])
async def get_history(
    limit: int = Query(default=100, ge=1, le=1000),
    format: str = Query(default="full", description="'full' or 'simple'"),
):
    """
    Get result history in different formats

    - **format=simple**: Returns just results string (e.g., "PBBTPPB")
    - **format=full**: Returns full result objects
    """
    results = await db.get_recent_results(limit)

    if format == "simple":
        # Return BacVision-compatible format
        return {
            "ok": True,
            "data": [
                {
                    "value": r.get("result"),
                    "score": (
                        r.get("banker_score")
                        if r.get("result") == "B"
                        else r.get("player_score")
                    ),
                    "criado_em": r.get("timestamp"),
                }
                for r in results
            ],
        }

    return {"ok": True, "data": results}


@app.get("/api/statistics", response_model=Statistics, tags=["Analysis"])
async def get_statistics(
    hours: int = Query(default=24, ge=1, le=168, description="Hours to analyze (1-168)"),
):
    """
    Get statistics for a time period

    - **hours**: Number of hours to analyze (default: 24)
    """
    return await db.get_statistics(hours)


@app.get("/api/streak", response_model=Streak, tags=["Analysis"])
async def get_current_streak():
    """Get current winning streak"""
    return await db.get_current_streak()


@app.get("/api/pattern", tags=["Analysis"])
async def get_pattern(length: int = Query(default=20, ge=5, le=100)):
    """
    Get recent pattern for Big Road analysis

    Returns array of results for pattern matching
    """
    results = await db.get_recent_results(length)

    # Reverse to get chronological order (oldest first)
    results = list(reversed(results))

    pattern = []
    for r in results:
        pattern.append(
            {
                "result": r.get("result"),
                "player_score": r.get("player_score"),
                "banker_score": r.get("banker_score"),
                "is_natural": r.get("is_natural", False),
            }
        )

    return {
        "pattern": pattern,
        "string": "".join(r["result"] for r in pattern if r["result"]),
        "length": len(pattern),
    }


@app.get("/api/roads", tags=["Analysis"])
async def get_roads_data(limit: int = Query(default=50, ge=10, le=200)):
    """
    Get data formatted for Big Road and derived roads analysis
    """
    results = await db.get_recent_results(limit)
    results = list(reversed(results))  # Chronological order

    # Build Big Road format
    big_road: list = []
    current_column: list = []
    current_result = None

    for r in results:
        result = r.get("result")
        if result == "T":
            # Ties don't change columns
            if current_column:
                current_column[-1]["ties"] = current_column[-1].get("ties", 0) + 1
            continue

        if result != current_result:
            # New column
            if current_column:
                big_road.append(current_column)
            current_column = [{"result": result, "ties": 0}]
            current_result = result
        else:
            # Continue column
            current_column.append({"result": result, "ties": 0})

    if current_column:
        big_road.append(current_column)

    return {
        "big_road": big_road,
        "total_columns": len(big_road),
        "last_result": results[-1].get("result") if results else None,
        "results_count": len(results),
    }


# ============== Run Server ==============


def run_server():
    """Run the API server"""
    uvicorn.run(
        "api_server:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
