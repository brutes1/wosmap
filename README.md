# Tactile Map Generator

Generate 3D-printable tactile maps for the visually impaired. Enter an address or GPS coordinates, customize print settings, and receive an STL file ready for 3D printing. Optionally send directly to a Bambu X1C printer.

Based on the [touch-mapper](https://github.com/skarkkai/touch-mapper) project, adapted for local Docker execution.

## Quick Start

```bash
# Clone the repository
git clone <repo-url>
cd tactile-map-generator

# Start all services
docker-compose up --build

# Open in browser
open http://localhost:8080
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Docker Compose Stack                         │
├─────────────────────────────────────────────────────────────────────┤
│  Frontend (Vue 3)  →  Backend (FastAPI)  →  Converter (OSM2World)   │
│      :8080               :8000                                       │
│                              ↓                                       │
│                          Redis (Queue)                               │
└─────────────────────────────────────────────────────────────────────┘
```

### Components

| Service | Technology | Port | Purpose |
|---------|------------|------|---------|
| Frontend | Vue 3 + Nginx | 8080 | Web UI for map generation |
| Backend | FastAPI | 8000 | REST API, job management |
| Converter | Java + Python + Blender | - | OSM → STL conversion |
| Redis | Redis 7 | 6379 | Job queue, status storage |

## Usage

### Web Interface

1. Open http://localhost:8080
2. Enter an address or GPS coordinates
3. Adjust print settings:
   - **Scale**: 1:3463 (default) - larger scale = smaller area, more detail
   - **Size**: 23cm (default) - physical print size
   - **Include buildings**: Toggle building inclusion
4. Click "Generate Map"
5. Download the STL file when complete

### API Endpoints

```bash
# Create a map from an address
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"address": "123 Main St, San Francisco, CA", "scale": 3463, "size_cm": 23}'

# Create a map from coordinates
curl -X POST http://localhost:8000/api/maps \
  -H "Content-Type: application/json" \
  -d '{"latitude": 37.7749, "longitude": -122.4194, "scale": 3463, "size_cm": 23}'

# Check job status
curl http://localhost:8000/api/maps/{job_id}

# Download STL
curl -O http://localhost:8000/api/maps/{job_id}/download
```

## Print Settings

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Scale | 1:3463 | 1:1000 - 1:10000 | Map scale (1:1000 = very detailed) |
| Size | 23cm | 5-50cm | Physical print size |
| Buildings | On | On/Off | Include building footprints |

### Recommended Settings by Use Case

- **City block**: Scale 1:1000-2000, Size 15-20cm
- **Neighborhood**: Scale 1:3000-4000, Size 20-25cm
- **District**: Scale 1:5000-7500, Size 20-30cm

## Bambu X1C Printer Integration

### Requirements

1. Bambu X1C with Developer Mode enabled
2. Printer on same local network
3. OrcaSlicer installed for slicing

### Setup

1. Enable Developer Mode on your printer:
   - Go to Settings → General → Developer Mode
   - Toggle ON
   - Note: This disables cloud features

2. Get printer credentials:
   - IP Address: Settings → WLAN → IP
   - Access Code: Settings → WLAN → Access Code (8 digits)
   - Serial Number: Settings → Device Info

3. Configure in the web UI:
   - Click "Send to Printer" on a completed map
   - Enter printer credentials
   - Click "Save & Print"

## Data Sources

### OpenStreetMap (Default)
- Real-time data via Overpass API
- Good coverage worldwide
- Includes buildings, roads, water, railways

### OSM + Microsoft Buildings
- Enhanced building coverage
- Microsoft's ML-derived building footprints
- Better for areas with sparse OSM data

## Development

### Local Development

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# Frontend
cd frontend
npm install
npm run dev

# Converter (requires Java 8 and Blender)
cd converter
python worker.py
```

### Building Docker Images

```bash
# Build all
docker-compose build

# Build specific service
docker-compose build converter
```

## Troubleshooting

### "Map generation failed"
- Check converter logs: `docker-compose logs converter`
- Common causes:
  - OSM data not available for area
  - Memory limit exceeded (increase in docker-compose.yml)

### "Cannot connect to Redis"
- Ensure Redis is running: `docker-compose ps`
- Check Redis health: `docker-compose exec redis redis-cli ping`

### Printer not responding
- Verify Developer Mode is enabled
- Check IP address and access code
- Ensure printer is on same network

## License

This project is licensed under AGPL-3.0, following the touch-mapper license.

## Credits

- [touch-mapper](https://github.com/skarkkai/touch-mapper) - Original tactile map generation
- [OSM2World](https://osm2world.org/) - OSM to 3D conversion
- [OpenStreetMap](https://www.openstreetmap.org/) - Map data
- [Microsoft Building Footprints](https://github.com/microsoft/GlobalMLBuildingFootprints) - Building data
