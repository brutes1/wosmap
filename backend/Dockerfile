# Backend API service with OrcaSlicer for 3MF generation
FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive

WORKDIR /app

# Install Python and system dependencies including OrcaSlicer requirements
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    curl \
    wget \
    # OrcaSlicer dependencies
    xvfb \
    libgtk-3-0 \
    libwebkit2gtk-4.0-37 \
    libgstreamer1.0-0 \
    libgstreamer-plugins-base1.0-0 \
    libglu1-mesa \
    libsecret-1-0 \
    libnotify4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libatspi2.0-0 \
    libgl1-mesa-glx \
    libxkbcommon0 \
    fuse \
    && rm -rf /var/lib/apt/lists/*

# Install OrcaSlicer by extracting AppImage using p7zip
# This works during cross-platform builds (ARM host building x86_64) without executing the binary
RUN apt-get update && apt-get install -y p7zip-full && \
    ORCA_VERSION="2.2.0" && \
    echo "Installing OrcaSlicer ${ORCA_VERSION}..." && \
    wget -q "https://github.com/SoftFever/OrcaSlicer/releases/download/v${ORCA_VERSION}/OrcaSlicer_Linux_V${ORCA_VERSION}.AppImage" \
        -O /tmp/OrcaSlicer.AppImage && \
    cd /tmp && \
    7z x -o/opt/orcaslicer OrcaSlicer.AppImage && \
    rm /tmp/OrcaSlicer.AppImage && \
    chmod +x /opt/orcaslicer/AppRun && \
    find /opt/orcaslicer -type f -name "*.so*" -exec chmod +x {} \; && \
    find /opt/orcaslicer -type f -name "orca*" -exec chmod +x {} \; && \
    ln -s /opt/orcaslicer/AppRun /usr/local/bin/orca-slicer && \
    apt-get remove -y p7zip-full && apt-get autoremove -y && \
    rm -rf /var/lib/apt/lists/* && \
    echo "OrcaSlicer installed successfully"

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY backend/*.py .
COPY backend/profiles ./profiles
COPY converter/multicolor_3mf.py .

# Environment variables
ENV REDIS_HOST=redis
ENV REDIS_PORT=6379
ENV MAPS_DIR=/data/maps
ENV PYTHONUNBUFFERED=1
ENV ORCASLICER_PATH=/usr/local/bin/orca-slicer

# Create data directory
RUN mkdir -p /data/maps

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/api/health || exit 1

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
