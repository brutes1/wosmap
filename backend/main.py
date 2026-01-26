"""
FastAPI backend for tactile map generation.
Handles job submission, status checking, and file downloads.
"""

import os
import json
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import redis

from geocoding import geocode_address, reverse_geocode


# Configuration
REDIS_HOST = os.environ.get("REDIS_HOST", "localhost")
REDIS_PORT = int(os.environ.get("REDIS_PORT", 6379))
MAPS_DIR = Path(os.environ.get("MAPS_DIR", "/data/maps"))
ALLOWED_ORIGINS = os.environ.get("ALLOWED_ORIGINS", "http://localhost:8080").split(",")

# Printer configuration from environment (more secure than Redis storage)
PRINTER_IP = os.environ.get("PRINTER_IP")
PRINTER_ACCESS_CODE = os.environ.get("PRINTER_ACCESS_CODE")
PRINTER_SERIAL = os.environ.get("PRINTER_SERIAL")


# Initialize FastAPI
app = FastAPI(
    title="WOSMap API",
    description="Generate 3D-printable tactile maps from geographic data",
    version="1.0.0",
)

# CORS middleware for frontend
# Security: Only allow specific origins (configured via ALLOWED_ORIGINS env var)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
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
    data_source: str = Field("osm", description="Data source: 'osm' or 'overture' (osm_ms accepted for backwards compatibility)")


class MapResponse(BaseModel):
    """Response after submitting a map request."""
    job_id: str
    status: str
    message: str


class JobStatus(BaseModel):
    """Status of a map generation job."""
    job_id: str
    status: str
    stage_message: Optional[str] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    files: Optional[dict] = None
    file_info: Optional[dict] = None
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
    return {"status": "ok", "service": "wosmap"}


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

    # Get location name for file naming
    location_name = await reverse_geocode(lat, lon)
    if location_name is None:
        # Fallback to coordinates
        location_name = f"{lat:.3f}_{lon:.3f}"

    # Create job payload
    job = {
        "id": job_id,
        "latitude": lat,
        "longitude": lon,
        "scale": request.scale,
        "size_cm": request.size_cm,
        "include_buildings": request.include_buildings,
        "data_source": request.data_source,
        "location_name": location_name,
        "created_at": datetime.utcnow().isoformat(),
    }

    # Add to Redis queue
    r = get_redis()
    r.lpush("map_jobs", json.dumps(job))

    # Store initial status
    r.set(f"result:{job_id}", json.dumps({
        "status": "queued",
        "job_id": job_id,
        "location_name": location_name,
        "created_at": job["created_at"],
    }))

    return MapResponse(
        job_id=job_id,
        status="queued",
        message="Map generation job submitted successfully"
    )


@app.get("/api/maps")
async def list_maps():
    """List all map generation jobs."""
    r = get_redis()
    jobs = []

    # Get all result keys
    for key in r.scan_iter("result:*"):
        data = json.loads(r.get(key))
        job_id = key.replace("result:", "")
        jobs.append({
            "job_id": job_id,
            "status": data.get("status"),
            "location_name": data.get("location_name"),
            "created_at": data.get("created_at"),
            "file_info": data.get("file_info"),
        })

    # Sort by created_at descending
    jobs.sort(key=lambda x: x.get("created_at") or "", reverse=True)
    return {"jobs": jobs}


@app.delete("/api/maps")
async def clear_history():
    """Delete all completed map jobs and their files."""
    r = get_redis()
    deleted_count = 0

    for key in r.scan_iter("result:*"):
        data = json.loads(r.get(key))

        # Delete files if they exist
        files = data.get("files", {})
        for file_type, file_path in files.items():
            path = Path(file_path)
            if path.exists():
                # Delete the job directory (all files in same dir)
                if path.parent.exists():
                    shutil.rmtree(path.parent)
                    break

        # Delete Redis key
        r.delete(key)
        deleted_count += 1

    return {"deleted": deleted_count, "message": f"Deleted {deleted_count} jobs"}


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
        stage_message=data.get("stage_message"),
        created_at=data.get("created_at"),
        updated_at=data.get("updated_at"),
        files=data.get("files"),
        file_info=data.get("file_info"),
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

    # Security: Validate file is within MAPS_DIR to prevent path traversal
    try:
        if not file_path.resolve().is_relative_to(MAPS_DIR.resolve()):
            raise HTTPException(status_code=403, detail="Access denied")
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found on disk")

    # Determine content type
    content_types = {
        "stl": "application/sla",
        "svg": "image/svg+xml",
        "blend": "application/octet-stream",
        "pdf": "application/pdf",
    }

    # Generate user-friendly filename: wosmap_[location]_[date].stl
    location_name = data.get("location_name", "map")
    created_at = data.get("created_at", "")
    if created_at:
        # Extract date from ISO timestamp
        date_str = created_at.split("T")[0]
    else:
        date_str = datetime.utcnow().strftime("%Y-%m-%d")

    filename = f"wosmap_{location_name}_{date_str}.{file_type}"

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type=content_types.get(file_type, "application/octet-stream")
    )


# ============================================
# Printer Configuration Endpoints
# ============================================

@app.post("/api/printer/config")
async def configure_printer(config: PrinterConfig):
    """
    Configure the Bambu X1C printer for LAN printing.

    Note: For production, set PRINTER_IP, PRINTER_ACCESS_CODE, and PRINTER_SERIAL
    environment variables instead of using this endpoint.
    """
    # Security: Store minimal info in Redis (not the access code)
    r = get_redis()
    r.set("printer_config", json.dumps({
        "ip": config.ip,
        "serial": config.serial,
        # Access code stored separately or use env var
        "configured_at": datetime.utcnow().isoformat(),
    }))
    # Store access code with short TTL (1 hour) for immediate use
    r.setex(f"printer_access:{config.serial}", 3600, config.access_code)
    return {"status": "configured", "message": "Printer configuration saved (access code expires in 1 hour)"}


def get_printer_config() -> dict:
    """
    Get printer configuration from environment or Redis.
    Environment variables take precedence for security.
    """
    # Prefer environment variables
    if PRINTER_IP and PRINTER_ACCESS_CODE and PRINTER_SERIAL:
        return {
            "ip": PRINTER_IP,
            "access_code": PRINTER_ACCESS_CODE,
            "serial": PRINTER_SERIAL,
        }

    # Fall back to Redis
    r = get_redis()
    config = r.get("printer_config")
    if config is None:
        return None

    data = json.loads(config)
    # Get access code from separate key (with TTL)
    access_code = r.get(f"printer_access:{data.get('serial')}")
    if not access_code:
        return None

    return {
        "ip": data["ip"],
        "access_code": access_code,
        "serial": data["serial"],
    }


@app.post("/api/printer/test")
async def test_printer_connection():
    """Test connection to the configured printer."""
    config = get_printer_config()

    if config is None:
        raise HTTPException(
            status_code=400,
            detail="Printer not configured. Set PRINTER_* env vars or use POST /api/printer/config."
        )

    from printer import BambuPrinter, PrinterError

    try:
        printer = BambuPrinter(
            ip=config["ip"],
            access_code=config["access_code"],
            serial=config["serial"]
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
async def get_printer_config_endpoint():
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
    # Check printer is configured
    printer_config = get_printer_config()
    if printer_config is None:
        raise HTTPException(
            status_code=400,
            detail="Printer not configured. Set PRINTER_* env vars or use POST /api/printer/config."
        )

    r = get_redis()

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

    # Run the slice and print workflow
    try:
        result = slice_and_print(
            stl_path=stl_path,
            printer_config=printer_config,
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
