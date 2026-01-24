---
title: "feat: Local Tactile Map Generator with Bambu X1C Integration"
type: feat
date: 2026-01-24
---

# Local Tactile Map Generator with Bambu X1C Integration

## Overview

Build a self-contained Docker application that generates 3D-printable tactile maps from geographic data. Users enter an address or GPS coordinates, customize print settings (scale, size), and receive an STL file. Optionally send directly to a Bambu X1C printer over LAN.

Based on the open-source [touch-mapper](https://github.com/skarkkai/touch-mapper) project, adapted for local execution without AWS dependencies.

## Problem Statement / Motivation

The existing touch-mapper.org service is cloud-dependent and doesn't support:
- Local/offline operation
- Direct printer integration
- Alternative map data sources
- Custom deployment for privacy-sensitive use cases

A local Docker solution enables:
- Full control over the pipeline
- Direct Bambu X1C printer integration
- Offline capability (with pre-downloaded map data)
- Customization for specific use cases (e.g., indoor maps, custom overlays)

## Proposed Solution

### Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose Stack                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌──────────────┐    ┌─────────────────────┐     │
│  │   Frontend  │───▶│   Backend    │───▶│   Converter Worker  │     │
│  │  (Nginx +   │    │  (FastAPI)   │    │  (OSM2World +       │     │
│  │   Vue/React)│◀───│              │◀───│   Blender)          │     │
│  └─────────────┘    └──────────────┘    └─────────────────────┘     │
│        :8080              :8000                   │                   │
│                              │                    │                   │
│                              ▼                    ▼                   │
│                    ┌──────────────┐    ┌─────────────────────┐       │
│                    │    Redis     │    │   Shared Volume     │       │
│                    │   (Queue)    │    │   /data/maps        │       │
│                    └──────────────┘    └─────────────────────┘       │
│                                                   │                   │
└───────────────────────────────────────────────────│───────────────────┘
                                                    │
                              ┌─────────────────────┴────────────────┐
                              ▼                                      ▼
                    ┌─────────────────┐                    ┌─────────────────┐
                    │  Map Data APIs  │                    │   Bambu X1C     │
                    │  (Overpass,     │                    │   (MQTT/FTPS)   │
                    │   MS Buildings) │                    │   :8883/:990    │
                    └─────────────────┘                    └─────────────────┘
```

### Components

| Component | Technology | Purpose |
|-----------|------------|---------|
| Frontend | Vue 3 + Vite | Minimal UI for map input and settings |
| Backend API | FastAPI (Python) | REST API, job management, printer integration |
| Job Queue | Redis | Replace AWS SQS with local queue |
| Converter | Java (OSM2World) + Python + Blender | Map data → STL pipeline |
| Storage | Docker volume | Replace S3 with local filesystem |
| Printer Client | bambulabs_api + BambuStudio CLI | Slice and send to X1C |

## Technical Approach

### Phase 1: Core Pipeline (Containerized touch-mapper)

**Goal:** Get the OSM → STL conversion working in Docker.

#### 1.1 Dockerfile for Converter Service

```dockerfile
# converter/Dockerfile
FROM ubuntu:22.04

# Install Java 8, Python 3, graphics libs
RUN apt-get update && apt-get install -y \
    openjdk-8-jre-headless \
    python3 python3-pip \
    libgl1-mesa-glx libxrender1 \
    wget curl

# Install Python dependencies
RUN pip3 install requests cairosvg

# Download and extract Blender (headless)
RUN wget -q https://download.blender.org/release/Blender3.6/blender-3.6.0-linux-x64.tar.xz \
    && tar -xf blender-3.6.0-linux-x64.tar.xz -C /opt \
    && ln -s /opt/blender-3.6.0-linux-x64/blender /usr/local/bin/blender

# Copy OSM2World JAR (pre-built)
COPY OSM2World/build/OSM2World.jar /app/OSM2World.jar

# Copy converter scripts
COPY converter/ /app/converter/

WORKDIR /app
ENV JAVA_OPTS="-Xmx1G"

ENTRYPOINT ["python3", "/app/converter/worker.py"]
```

#### 1.2 Local Worker Script (Replace AWS Poller)

```python
# converter/worker.py
import redis
import json
from process_request import process_map_request

r = redis.Redis(host='redis', port=6379)

while True:
    # Block until job available
    _, job_data = r.brpop('map_jobs')
    job = json.loads(job_data)

    try:
        result = process_map_request(job)
        r.set(f"result:{job['id']}", json.dumps(result))
    except Exception as e:
        r.set(f"result:{job['id']}", json.dumps({'error': str(e)}))
```

#### 1.3 Modified process_request.py

Key changes from original:
- Remove AWS S3/SQS calls
- Write outputs to local `/data/maps/{job_id}/`
- Add support for alternative map data sources

**Files to create/modify:**
- `converter/worker.py` - Redis-based job consumer
- `converter/process_request.py` - Adapted from touch-mapper
- `converter/osm_sources.py` - Map data source abstraction

### Phase 2: Backend API

**Goal:** REST API for job submission and status checking.

#### 2.1 FastAPI Application

```python
# backend/main.py
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import redis
import uuid

app = FastAPI()
r = redis.Redis(host='redis', port=6379)

class MapRequest(BaseModel):
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    scale: int = 3463  # Default per user request
    size_cm: float = 23.0  # Default per user request
    include_buildings: bool = True
    data_source: str = "osm"  # osm, osm_ms (with Microsoft buildings)

@app.post("/api/maps")
async def create_map(request: MapRequest):
    job_id = str(uuid.uuid4())
    job = {
        "id": job_id,
        **request.dict()
    }
    r.lpush('map_jobs', json.dumps(job))
    return {"job_id": job_id, "status": "queued"}

@app.get("/api/maps/{job_id}")
async def get_map_status(job_id: str):
    result = r.get(f"result:{job_id}")
    if result:
        return json.loads(result)
    return {"status": "processing"}

@app.get("/api/maps/{job_id}/download")
async def download_map(job_id: str):
    # Return STL file from /data/maps/{job_id}/
    ...
```

**Files to create:**
- `backend/main.py` - FastAPI app
- `backend/geocoding.py` - Address → coordinates (using Nominatim)
- `backend/requirements.txt`

### Phase 3: Frontend UI

**Goal:** Minimal single-page interface.

#### 3.1 UI Components

```
┌─────────────────────────────────────────────────┐
│  Tactile Map Generator                          │
├─────────────────────────────────────────────────┤
│                                                 │
│  Location:                                      │
│  ┌─────────────────────────────────────────┐   │
│  │ 123 Main St, City, State               │   │
│  └─────────────────────────────────────────┘   │
│  [ ] Use GPS coordinates instead               │
│      Lat: [______] Lon: [______]               │
│                                                 │
│  Print Settings:                                │
│  Scale: [ 1:3463 ▼ ]  Size: [ 23 ] cm          │
│  [ ] Include buildings                          │
│                                                 │
│  Data Source:                                   │
│  ( ) OpenStreetMap (default)                   │
│  ( ) OSM + Microsoft Buildings (better coverage)│
│                                                 │
│  [ Generate Map ]                               │
│                                                 │
│  ─────────────────────────────────────────────  │
│  Status: Processing... (45%)                    │
│                                                 │
│  [ Download STL ] [ Send to Printer ]           │
│                                                 │
└─────────────────────────────────────────────────┘
```

**Files to create:**
- `frontend/src/App.vue` - Main component
- `frontend/src/api.js` - Backend API client
- `frontend/Dockerfile` - Nginx serving built Vue app

### Phase 4: Bambu X1C Printer Integration

**Goal:** Slice STL and send to printer over LAN.

#### 4.1 Prerequisites
- **Developer Mode** must be enabled on the X1C
- User must provide: IP address, Access Code (8-digit), Serial Number

#### 4.2 Printer Integration Flow

```
STL File
    │
    ▼
┌─────────────────────────┐
│ BambuStudio CLI         │  (Slice to .gcode.3mf)
│ --export-3mf            │
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ FTPS Upload             │  Port 990, user: bblp
│ to /cache/ on printer   │  pass: LAN Access Code
└─────────────────────────┘
    │
    ▼
┌─────────────────────────┐
│ MQTT Command            │  Port 8883
│ project_file            │  Start print job
└─────────────────────────┘
```

#### 4.3 Printer Service Code

```python
# backend/printer.py
import bambulabs_api as bl
import subprocess
import ftplib
import ssl

class BambuPrinter:
    def __init__(self, ip: str, access_code: str, serial: str):
        self.ip = ip
        self.access_code = access_code
        self.serial = serial

    def slice_stl(self, stl_path: str, output_path: str):
        """Use BambuStudio CLI to slice STL to 3MF"""
        subprocess.run([
            "bambu-studio",
            "--export-3mf", output_path,
            "--load-settings", "/app/profiles/tactile_map.json",
            stl_path
        ], check=True)

    def upload_and_print(self, gcode_3mf_path: str):
        """Upload via FTPS and start print via MQTT"""
        # Upload file
        context = ssl.create_default_context()
        ftp = ftplib.FTP_TLS()
        ftp.connect(self.ip, 990)
        ftp.login("bblp", self.access_code)
        ftp.prot_p()

        filename = os.path.basename(gcode_3mf_path)
        with open(gcode_3mf_path, 'rb') as f:
            ftp.storbinary(f'STOR /cache/{filename}', f)
        ftp.quit()

        # Start print via MQTT
        printer = bl.Printer(self.ip, self.access_code, self.serial)
        printer.connect()
        printer.start_print(f'/cache/{filename}')
        printer.disconnect()
```

#### 4.4 Printer Configuration API

```python
# backend/main.py additions
class PrinterConfig(BaseModel):
    ip: str
    access_code: str
    serial: str

@app.post("/api/printer/config")
async def configure_printer(config: PrinterConfig):
    # Store in Redis or config file
    r.set("printer_config", json.dumps(config.dict()))
    return {"status": "configured"}

@app.post("/api/maps/{job_id}/print")
async def send_to_printer(job_id: str):
    config = json.loads(r.get("printer_config"))
    printer = BambuPrinter(**config)

    stl_path = f"/data/maps/{job_id}/map.stl"
    gcode_path = f"/data/maps/{job_id}/map.gcode.3mf"

    printer.slice_stl(stl_path, gcode_path)
    printer.upload_and_print(gcode_path)

    return {"status": "sent_to_printer"}
```

**Files to create:**
- `backend/printer.py` - Bambu X1C client
- `backend/profiles/tactile_map.json` - Default slicing profile for tactile maps

### Phase 5: Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  frontend:
    build: ./frontend
    ports:
      - "8080:80"
    depends_on:
      - backend

  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - REDIS_HOST=redis
    volumes:
      - map_data:/data/maps
    depends_on:
      - redis

  converter:
    build: ./converter
    environment:
      - REDIS_HOST=redis
    volumes:
      - map_data:/data/maps
    depends_on:
      - redis
    deploy:
      resources:
        limits:
          memory: 4G

  redis:
    image: redis:7-alpine
    volumes:
      - redis_data:/data

volumes:
  map_data:
  redis_data:
```

## Data Sources Implementation

### OpenStreetMap (Primary)

```python
# converter/osm_sources.py
import requests

def fetch_osm_data(bbox: tuple, timeout: int = 180) -> str:
    """Fetch OSM data via Overpass API"""
    query = f"""
    [out:xml][timeout:{timeout}];
    (
      way["building"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["highway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["railway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      way["waterway"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
      relation["building"]({bbox[0]},{bbox[1]},{bbox[2]},{bbox[3]});
    );
    out geom;
    """

    endpoints = [
        "https://overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
    ]

    for endpoint in endpoints:
        try:
            response = requests.post(endpoint, data=query, timeout=timeout+30)
            if response.status_code == 200:
                return response.text
        except requests.RequestException:
            continue

    raise Exception("All Overpass endpoints failed")
```

### Microsoft Building Footprints (Supplementary)

```python
def fetch_microsoft_buildings(bbox: tuple) -> list:
    """Fetch Microsoft building footprints for the area"""
    # Microsoft provides data in quadkey-indexed files
    # For a real implementation, determine which quadkey tiles
    # intersect the bbox and download those

    # Note: This requires pre-downloading or caching the data
    # as Microsoft doesn't provide a real-time query API
    pass
```

### Data Source Availability Matrix

| Source | Buildings | Roads | Water | Terrain | Real-time API | License |
|--------|-----------|-------|-------|---------|--------------|---------|
| OpenStreetMap | Yes | Yes | Yes | No | Yes (Overpass) | ODbL |
| Microsoft Buildings | Yes (+heights) | No | No | No | No (bulk download) | ODbL |
| USGS/SRTM | No | No | No | Yes | No (bulk download) | Public Domain |

**Note:** Mapbox and Google Maps are **not viable** due to Terms of Service prohibiting data extraction.

## Acceptance Criteria

### Functional Requirements
- [x] User can enter address OR GPS coordinates
- [x] User can set scale (default 1:3463) and size (default 23cm)
- [x] User can toggle building inclusion
- [x] User can select data source (OSM or OSM+Microsoft)
- [x] System generates valid STL file for 3D printing
- [x] User can download generated STL
- [x] User can configure Bambu X1C printer (IP, access code, serial)
- [x] User can send STL directly to configured printer

### Non-Functional Requirements
- [x] All components run in Docker containers
- [ ] Works offline once map data is cached
- [ ] Conversion completes within 5 minutes for typical map sizes
- [x] Frontend responsive on desktop browsers

### Quality Gates
- [ ] docker-compose up starts all services successfully
- [ ] End-to-end test: address → STL download works
- [ ] Printer integration tested with actual X1C

## Dependencies & Risks

### Dependencies
| Dependency | Risk Level | Mitigation |
|------------|------------|------------|
| Overpass API availability | Low | Multiple fallback endpoints |
| Blender download (~300MB) | Low | Cache in Docker image |
| BambuStudio CLI | Medium | May need to build from source or use alternative slicer |
| bambulabs_api library | Medium | Library still maintained; fallback to raw MQTT/FTP |

### Risks
1. **BambuStudio CLI availability** - Bambu Lab doesn't officially distribute a CLI. May need to:
   - Use OrcaSlicer CLI instead (open source fork)
   - Or integrate PrusaSlicer CLI with Bambu printer profiles

2. **Bambu firmware changes** - Post-2025 firmware requires Developer Mode. Users must enable this manually.

3. **Map data completeness** - OSM coverage varies by region. Microsoft Buildings helps but has no roads.

## File Structure

```
tactile-map-generator/
├── docker-compose.yml
├── README.md
├── .env.example
│
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.js
│   └── src/
│       ├── App.vue
│       ├── main.js
│       └── api.js
│
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── geocoding.py
│   ├── printer.py
│   └── profiles/
│       └── tactile_map.json
│
├── converter/
│   ├── Dockerfile
│   ├── worker.py
│   ├── process_request.py
│   ├── osm_sources.py
│   ├── osm_to_tactile.py
│   └── obj_to_tactile.py
│
└── OSM2World/
    └── build/
        └── OSM2World.jar
```

## References & Research

### Internal References
- touch-mapper repository analysis (converter pipeline, OSM2World integration)

### External References
- [touch-mapper GitHub](https://github.com/skarkkai/touch-mapper)
- [OSM2World](https://osm2world.org/)
- [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API)
- [Microsoft Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints)
- [bambulabs_api](https://github.com/BambuTools/bambulabs_api)
- [Bambu Lab Developer Mode](https://wiki.bambulab.com/en/knowledge-sharing/enable-developer-mode)
- [OrcaSlicer](https://github.com/SoftFever/OrcaSlicer) (open-source alternative slicer with CLI)
