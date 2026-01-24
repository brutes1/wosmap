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
    cairosvg

# Download and install Blender (LTS version for stability)
ENV BLENDER_VERSION=3.6.5
ENV BLENDER_URL=https://download.blender.org/release/Blender3.6/blender-${BLENDER_VERSION}-linux-x64.tar.xz
RUN wget -q ${BLENDER_URL} -O /tmp/blender.tar.xz \
    && mkdir -p /opt/blender \
    && tar -xf /tmp/blender.tar.xz -C /opt/blender --strip-components=1 \
    && rm /tmp/blender.tar.xz \
    && ln -s /opt/blender/blender /usr/local/bin/blender

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
ENV BLENDER_PATH=/usr/local/bin/blender
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
