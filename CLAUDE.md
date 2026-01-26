# CLAUDE.md - AI Assistant Guide for WOSMap

This document provides context and guidelines for AI assistants working with the WOSMap codebase.

## Project Overview

**WOSMap** (Worth One's Salt Map) is a tactile map generator that creates 3D-printable maps for the visually impaired. Users enter an address or GPS coordinates, customize print settings, and receive an STL file ready for 3D printing. Optional integration with Bambu X1C printers for direct printing.

Based on the [touch-mapper](https://github.com/skarkkai/touch-mapper) project, optimized for local Docker execution.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Compose Stack                      │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Vue 3 + Nginx)  :8080                            │
│         ↓ HTTP/REST                                          │
│  Backend (FastAPI)         :8000                            │
│         ↓ JSON/Redis                                         │
│  Redis Queue               (internal only)                   │
│         ↑ Job messages                                       │
│  Converter Worker (Python + Java + Blender)                 │
└─────────────────────────────────────────────────────────────┘
```

### Data Flow
1. User submits address/coordinates via frontend
2. Backend creates job, pushes to Redis queue
3. Converter worker processes: OSM data → OSM2World → Blender → STL
4. Backend returns completed files via REST API

## Directory Structure

```
wosmap/
├── frontend/                 # Vue 3 web application
│   ├── src/
│   │   ├── App.vue          # Main UI component (~874 lines)
│   │   ├── api.js           # API client functions
│   │   └── components/
│   │       └── MapSelector.vue  # Leaflet map component
│   ├── Dockerfile           # Multi-stage: Node build → Nginx
│   ├── nginx.conf           # Static serving + API proxy
│   ├── package.json         # Vue 3, Leaflet, Vite
│   └── vite.config.js       # Build config with API proxy
│
├── backend/                  # FastAPI REST API
│   ├── main.py              # FastAPI server (~600 lines)
│   ├── geocoding.py         # Nominatim address/coordinate lookup
│   ├── printer.py           # Bambu X1C integration (MQTT/FTPS)
│   ├── profiles/            # OrcaSlicer print profiles
│   ├── requirements.txt     # Python dependencies
│   └── Dockerfile
│
├── converter/               # Map processing worker
│   ├── worker.py            # Redis job consumer
│   ├── process_request.py   # Main job orchestration
│   ├── osm_sources.py       # OSM/Overture data fetching
│   ├── osm-to-tactile.py    # OSM2World + Blender pipeline
│   ├── obj-to-tactile.py    # OBJ→STL conversion
│   ├── stl_utils.py         # STL parsing utilities
│   └── Dockerfile           # Multi-stage: Java build + Ubuntu runtime
│
├── OSM2World/               # Third-party Java library (submodule)
├── docs/                    # Documentation and plans
│   ├── plans/               # Feature implementation plans
│   └── solutions/           # Problem-solving documentation
│
├── docker-compose.yml       # Service orchestration
├── .env.example             # Configuration template
└── README.md                # User documentation
```

## Tech Stack

| Layer | Technology | Version |
|-------|-----------|---------|
| Frontend | Vue 3, Vite, Leaflet | 3.4, 5.0, 1.9.4 |
| Backend | FastAPI, Uvicorn, Pydantic | 0.109.0, 0.27.0, 2.5.3 |
| Queue | Redis | 7-alpine |
| Converter | Python 3.11, Java 8, Blender 3.0 | - |
| Slicing | OrcaSlicer (optional) | Latest |
| Geocoding | Nominatim API | - |

## Key Files Reference

### Backend (`backend/main.py`)
- **API Endpoints:**
  - `POST /api/maps` - Submit map generation request
  - `GET /api/maps` - List all jobs
  - `GET /api/maps/{job_id}` - Get job status + metadata
  - `GET /api/maps/{job_id}/download?file_type=stl|svg|3mf|blend` - Download files
  - `POST /api/maps/{job_id}/print` - Send to Bambu printer
  - `POST /api/printer/config` - Configure printer
  - `GET /api/capabilities` - Check OrcaSlicer availability
  - `GET /api/health` - Health check

### Frontend (`frontend/src/App.vue`)
- Single-file Vue component with all UI logic
- Reactive state management via Vue 3 Composition API
- Progress stages: queued → fetching_osm → fetching_overture → converting → finalizing

### Converter (`converter/process_request.py`)
- Main job orchestration function: `process_map_request()`
- Pipeline stages with callback support for status updates
- Outputs: STL, SVG, Blend files + metadata JSON

## Development Commands

```bash
# Start all services
docker-compose up --build

# Start specific service
docker-compose up backend

# View logs
docker-compose logs -f converter

# Rebuild single service
docker-compose build converter

# Local frontend development
cd frontend && npm install && npm run dev

# Local backend development
cd backend && pip install -r requirements.txt && uvicorn main:app --reload
```

## Coding Conventions

### Python (Backend/Converter)
- Use docstrings for modules and public functions
- Type hints for function parameters and returns
- Environment variables for configuration (no hardcoded values)
- Error handling with descriptive Exception messages
- Import order: stdlib → third-party → local

```python
"""Module docstring explaining purpose."""

import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
import redis

from geocoding import geocode_address


def process_job(job_id: str, params: dict) -> dict:
    """Process a map generation job.

    Args:
        job_id: Unique job identifier
        params: Job parameters dictionary

    Returns:
        Result dictionary with status and file paths
    """
    pass
```

### JavaScript/Vue (Frontend)
- ES modules with named exports
- JSDoc comments for exported functions
- Async/await for API calls
- Vue 3 Composition API patterns

```javascript
/**
 * Submit a map generation request.
 * @param {Object} params - Request parameters
 * @returns {Promise<Object>} Response with job_id
 */
export async function createMap(params) {
  const response = await fetch(`${API_BASE}/maps`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  if (!response.ok) {
    const error = await response.json()
    throw new Error(error.detail || 'Failed to create map')
  }
  return response.json()
}
```

### Pydantic Models
- Use descriptive Field() with validation constraints
- Document fields with description parameter

```python
class MapRequest(BaseModel):
    """Request to generate a tactile map."""
    address: Optional[str] = Field(None, description="Address to geocode")
    latitude: Optional[float] = Field(None, ge=-90, le=90, description="Center latitude")
    scale: int = Field(3463, ge=1000, le=10000, description="Map scale")
```

## Git Conventions

### Commit Messages
Use conventional commits format: `type(scope): description`

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation only
- `chore` - Maintenance tasks
- `refactor` - Code refactoring

**Scopes:** `frontend`, `backend`, `converter`, `api`, `3mf`, `progress`, `history`, `security`

**Examples from this repo:**
```
feat(3mf): add capability detection for optional OrcaSlicer
feat(history): add job history list with stats and clear functionality
fix(api): include stage_message and file_info in job status response
fix(security): address P1 critical security vulnerabilities
```

## Common Tasks

### Adding a New API Endpoint
1. Define Pydantic request/response models in `backend/main.py`
2. Add endpoint function with appropriate decorators
3. Update `frontend/src/api.js` with client function
4. Update frontend component to use new endpoint

### Adding a New Processing Stage
1. Add stage constant in `converter/process_request.py`
2. Call `update_stage(stage, message)` at appropriate point
3. Add stage to frontend's `stages` array in `App.vue`

### Modifying Docker Services
1. Update `docker-compose.yml` for service configuration
2. Update relevant `Dockerfile` for build changes
3. Test with `docker-compose up --build`

## Security Considerations

- **Redis not exposed**: Internal Docker network only (no host port)
- **CORS restricted**: Configure via `ALLOWED_ORIGINS` env var
- **Path traversal prevention**: File downloads validated against job directory
- **Printer credentials**: From environment variables, not stored in Redis
- **Input validation**: Pydantic models with range constraints

## Testing

No automated test suite currently. Manual testing approaches:

```bash
# Test converter directly
cd converter
python process_request.py --lat 37.7749 --lon -122.4194 --scale 3463

# Test API endpoints
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"latitude": 37.7749, "longitude": -122.4194}'

# Check health
curl http://localhost:8000/api/health
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `REDIS_HOST` | localhost | Redis server hostname |
| `REDIS_PORT` | 6379 | Redis server port |
| `MAPS_DIR` | /data/maps | Directory for generated files |
| `ALLOWED_ORIGINS` | http://localhost:8080 | CORS allowed origins |
| `PRINTER_IP` | - | Bambu X1C IP address |
| `PRINTER_ACCESS_CODE` | - | Bambu X1C access code |
| `PRINTER_SERIAL` | - | Bambu X1C serial number |

## Troubleshooting

### Common Issues

**"Map generation failed"**
- Check converter logs: `docker-compose logs converter`
- Common causes: OSM data unavailable, memory limit exceeded

**"Cannot connect to Redis"**
- Verify Redis running: `docker-compose ps`
- Test connection: `docker-compose exec redis redis-cli ping`

**Blender/ARM64 issues**
- Uses Ubuntu's Blender 3.0 package (headless, no GUI)
- See `docs/solutions/integration-issues/blender-python-arm64-compatibility.md`

### Useful Debug Commands
```bash
# Check all service status
docker-compose ps

# View specific service logs
docker-compose logs -f backend
docker-compose logs -f converter

# Redis queue inspection
docker-compose exec redis redis-cli
> LLEN map_jobs           # Queue length
> KEYS result:*           # Completed jobs
> GET result:<job_id>     # Job details
```

## Documentation

Additional documentation in `/docs`:
- `/docs/plans/` - Feature implementation plans with acceptance criteria
- `/docs/solutions/` - Problem-solving documentation for complex issues

## Dependencies Summary

### Backend (requirements.txt)
- fastapi, uvicorn - Web framework
- redis - Job queue client
- pydantic - Data validation
- httpx, requests - HTTP clients
- paho-mqtt - Printer communication

### Frontend (package.json)
- vue - UI framework
- leaflet - Interactive maps
- vite - Build tool

### Converter (Dockerfile)
- Python 3.11 - Processing scripts
- Java 8 - OSM2World JAR
- Blender 3.0 - 3D processing
- OrcaSlicer - STL→3MF slicing (optional)
