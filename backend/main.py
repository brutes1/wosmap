"""
FastAPI backend for tactile map generation.
Handles job submission, status checking, and file downloads.
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis

from geocoding import geocode_address


# Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
MAPS_DIR = Path(os.environ.get("MAPS_DIR", "/data/maps"))


# Initialize FastAPI
app = FastAPI(
    title="Tactile Map Generator API",
    description="Generate 3D-printable tactile maps from geographic data",
    version="1.0.0",
)

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Redis connection
redis_client: Optional[redis.Redis] = None


def get_redis() -> redis.Redis:
    """Get Redis client, creating if necessary."""
    global redis_client
    if redis_client is None:
        redis_client = redis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            decode_responses=True
        )
    return redis_client


# ============================================
# Request/Response Models
# ============================================

class MapRequest(BaseModel):
    """Request to generate a tactile map."""
    address: Optional[str] = Field(None, description="Address to geocode")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude")
    longitude: Optional[float] = Field(None, ge=-180, le=180, description="Center longitude")
    scale: int = Field(3463, ge=1000, le=10000, description="Map scale (e.g., 3463 for 1:3463)")
    size_cm: float = Field(23.0, ge=5, le=50, description="Print size in centimeters")
    include_buildings: bool = Field(True, description="Whether to include buildings")
    data_source: str = Field("osm", description="Data source: 'osm' or 'osm_ms'")


class MapResponse(BaseModel):
    """Response after submitting a map request."""
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Status of a map generation job."""
    job_id: str
    status: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    files: Optional[dict] = None
    error: Optional[str] = None
    metadata: Optional[dict] = None


class PrinterConfig(BaseModel):
    """Bambu X1C printer configuration."""
    ip: str = Field(..., description="Printer IP address")
    access_code: str = Field(..., min_length=8, max_length=8, description="8-digit access code")
    serial: str = Field(..., description="Printer serial number")


# ============================================
# API Endpoints
# ============================================

@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "tactile-map-generator"}


@app.get("/api/health")
async def health_check():
    """Detailed health check."""
    r = get_redis()
    try:
        r.ping()
        redis_status = "connected"
    except redis.ConnectionError:
        redis_status = "disconnected"

    return {
        "status": "ok",
        "redis": redis_status,
        "maps_dir": str(MAPS_DIR),
        "maps_dir_exists": MAPS_DIR.exists(),
    }


@app.post("/api/maps", response_model=MapResponse)
async def create_map(request: MapRequest):
    """
    Submit a new map generation request.

    Either address or latitude/longitude must be provided.
    """
    # Validate that we have location data
    if request.address is None and (request.latitude is None or request.longitude is None):
        raise HTTPException(
            status_code=400,
            detail="Either 'address' or both 'latitude' and 'longitude' must be provided"
        )

    # Geocode address if provided
    lat = request.latitude
    lon = request.longitude

    if request.address:
        geocode_result = await geocode_address(request.address)
        if geocode_result is None:
            raise HTTPException(
                status_code=400,
                detail=f"Could not geocode address: {request.address}"
            )
        lat = geocode_result["lat"]
        lon = geocode_result["lon"]

    # Generate job ID
    job_id = str(uuid.uuid4())

    # Create job payload
    job = {
        "id": job_id,
        "latitude": lat,
        "longitude": lon,
        "scale": request.scale,
        "size_cm": request.size_cm,
        "include_buildings": request.include_buildings,
        "data_source": request.data_source,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Add to Redis queue
    r = get_redis()
    r.lpush("map_jobs", json.dumps(job))

    # Store initial status
    r.set(f"result:{job_id}", json.dumps({
        "status": "queued",
        "job_id": job_id,
        "created_at": job["created_at"],
    }))

    return MapResponse(
        job_id=job_id,
        status="queued",
        message="Map generation job submitted successfully"
    )


@app.get("/api/maps/{job_id}", response_model=JobStatus)
async def get_map_status(job_id: str):
    """Get the status of a map generation job."""
    r = get_redis()
    result = r.get(f"result:{job_id}")

    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")

    data = json.loads(result)
    return JobStatus(
        job_id=job_id,
        status=data.get("status", "unknown"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        files=data.get("files"),
        error=data.get("error"),
        metadata=data.get("metadata"),
    )


@app.get("/api/maps/{job_id}/download")
async def download_map(job_id: str, file_type: str = "stl"):
    """
    Download a generated map file.

    Args:
        job_id: The job ID
        file_type: Type of file to download (stl, svg, blend)
    """
    r = get_redis()
    result = r.get(f"result:{job_id}")

    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")

    data = json.loads(result)

    if data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {data.get('status')}"
        )

    files = data.get("files", {})
    file_path = files.get(file_type)

    if file_path is None:
        raise HTTPException(
            status_code=404,
            detail=f"File type '{file_type}' not available. Available: {list(files.keys())}"
        )

    file_path = Path(file_path)
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine content type
    content_types = {
        "stl": "application/sla",
        "svg": "image/svg+xml",
        "blend": "application/octet-stream",
        "pdf": "application/pdf",
    }

    return FileResponse(
        path=file_path,
        filename=f"tactile_map_{job_id}.{file_type}",
        media_type=content_types.get(file_type, "application/octet-stream")
    )


# ============================================
# Printer Configuration Endpoints
# ============================================

@app.post("/api/printer/config")
async def configure_printer(config: PrinterConfig):
    """Configure the Bambu X1C printer for LAN printing."""
    r = get_redis()
    r.set("printer_config", json.dumps(config.dict()))
    return {"status": "configured", "message": "Printer configuration saved"}


@app.post("/api/printer/test")
async def test_printer_connection():
    """Test connection to the configured printer."""
    r = get_redis()
    config = r.get("printer_config")

    if config is None:
        raise HTTPException(
            status_code=400,
            detail="Printer not configured. Use POST /api/printer/config first."
        )

    from printer import BambuPrinter, PrinterError

    try:
        data = json.loads(config)
        printer = BambuPrinter(
            ip=data["ip"],
            access_code=data["access_code"],
            serial=data["serial"]
        )

        # Try to get printer status
        status = printer.get_status()
        return {
            "status": "connected",
            "message": "Successfully connected to printer",
            "printer_status": status
        }

    except PrinterError as e:
        return {
            "status": "error",
            "message": str(e)
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"Connection test failed: {str(e)}"
        }


@app.get("/api/printer/config")
async def get_printer_config():
    """Get the current printer configuration (without access code)."""
    r = get_redis()
    config = r.get("printer_config")

    if config is None:
        return {"status": "not_configured"}

    data = json.loads(config)
    # Don't expose the access code
    return {
        "status": "configured",
        "ip": data.get("ip"),
        "serial": data.get("serial"),
    }


@app.post("/api/maps/{job_id}/print")
async def send_to_printer(job_id: str):
    """
    Send a completed map to the configured Bambu X1C printer.

    This will:
    1. Slice the STL using OrcaSlicer
    2. Upload to printer via FTPS
    3. Start the print via MQTT
    """
    r = get_redis()

    # Check printer is configured
    printer_config = r.get("printer_config")
    if printer_config is None:
        raise HTTPException(
            status_code=400,
            detail="Printer not configured. Use POST /api/printer/config first."
        )

    # Check job status
    result = r.get(f"result:{job_id}")
    if result is None:
        raise HTTPException(status_code=404, detail="Job not found")

    data = json.loads(result)
    if data.get("status") != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Job is not completed. Current status: {data.get('status')}"
        )

    files = data.get("files", {})
    stl_path = files.get("stl")

    if stl_path is None:
        raise HTTPException(status_code=404, detail="STL file not found")

    # Import and use printer module
    from printer import slice_and_print, PrinterError

    config = json.loads(printer_config)

    # Run the slice and print workflow
    try:
        result = slice_and_print(
            stl_path=stl_path,
            printer_config=config,
            profile_path=None  # Use default tactile map profile
        )

        if result.get("status") in ["slice_failed", "upload_failed", "print_failed"]:
            raise HTTPException(
                status_code=500,
                detail=result.get("error", "Printing failed")
            )

        return {
            "status": "sent_to_printer",
            "message": "Print job sent to Bambu X1C",
            "job_id": job_id,
            "printer_result": result,
        }

    except PrinterError as e:
        raise HTTPException(
            status_code=500,
            detail=f"Printer error: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


# ============================================
# Startup/Shutdown
# ============================================

@app.on_event("startup")
async def startup_event():
    """Initialize on startup."""
    # Ensure maps directory exists
    MAPS_DIR.mkdir(parents=True, exist_ok=True)

    # Test Redis connection
    try:
        r = get_redis()
        r.ping()
        print(f"Connected to Redis at {REDIS_HOST}:{REDIS_PORT}")
    except redis.ConnectionError as e:
        print(f"Warning: Could not connect to Redis: {e}")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
