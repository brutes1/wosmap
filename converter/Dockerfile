# Multi-stage build for tactile map converter
# Stage 1: Build OSM2World JAR
# Stage 2: Runtime with Blender

# ============================================
# Stage 1: Build OSM2World
# ============================================
FROM ubuntu:22.04 AS osm2world-builder

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    openjdk-8-jdk \
    ant \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Copy OSM2World source
COPY OSM2World/ /build/OSM2World/

# Build JAR
RUN cd /build/OSM2World && ant jar

# ============================================
# Stage 2: Runtime
# ============================================
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Java runtime for OSM2World
    openjdk-8-jre-headless \
    # Python for scripts
    python3 \
    python3-pip \
    # Graphics libraries for Blender
    libgl1-mesa-glx \
    libxi6 \
    libxrender1 \
    libxkbcommon0 \
    libsm6 \
    libxfixes3 \
    libxxf86vm1 \
    # Utilities
    wget \
    curl \
    xz-utils \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip3 install --no-cache-dir \
    redis \
    requests \
    cairosvg \
    svgwrite \
    overturemaps \
    numpy \
    Pillow \
    numpy-stl

# Install Blender from Ubuntu repository (supports ARM64)
# Note: Ubuntu 22.04 provides Blender 3.0, which is older but works on ARM64
RUN apt-get update && apt-get install -y \
    blender \
    && rm -rf /var/lib/apt/lists/*

# Set up app directory
WORKDIR /app

# Copy OSM2World build from stage 1
COPY --from=osm2world-builder /build/OSM2World/build/OSM2World.jar /app/OSM2World.jar
COPY --from=osm2world-builder /build/OSM2World/build/lib /app/lib
COPY --from=osm2world-builder /build/OSM2World/build/resources /app/resources

# Copy converter scripts
COPY converter/*.py /app/converter/

# Set environment variables
ENV OSM2WORLD_JAR=/app/OSM2World.jar
ENV BLENDER_PATH=/usr/bin/blender
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV WORK_DIR=/data/maps
ENV PYTHONUNBUFFERED=1

# Create data directory
RUN mkdir -p /data/maps

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD python3 -c "import redis; r=redis.Redis(host='redis', port=6379); r.ping()" || exit 1

# Run worker
WORKDIR /app/converter
CMD ["python3", "worker.py"]
