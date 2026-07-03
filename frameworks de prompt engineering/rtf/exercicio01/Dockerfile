# ==============================================================================
# STAGE 1: Builder
# ==============================================================================
# Using official lightweight Python slim image for compilation phase
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files to disk and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install system build dependencies required for compiling specific Python wheels (if any)
# Keeping list minimal to reduce build footprint
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create a virtual environment to isolate installed dependencies cleanly
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install dependencies in the builder stage
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ==============================================================================
# STAGE 2: Runner
# ==============================================================================
# Base lightweight Python runtime image for execution
FROM python:3.11-slim AS runner

# Optimize Python execution environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8080

WORKDIR /app

# Create a dedicated, non-privileged system user and group (GID/UID 10001)
# Running as root is a major security risk in Kubernetes environments
RUN groupadd --gid 10001 appgroup && \
    useradd --uid 10001 --gid 10001 --shell /sbin/nologin --create-home appuser

# Copy the isolated virtual environment compiled during builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy source code and ensure the non-root user owns the files
# Preventing write privileges in runtime unless explicitly required
COPY app.py .
COPY lib/ ./lib/

# Set secure permissions so the non-root user can read files but not write to them
RUN chown -R appuser:appgroup /app

# Switch executing context to non-root user
USER 10001:10001

# Document exposed container port
EXPOSE 8080

# Production startup using gunicorn with standard optimized settings
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "4", "app:app"]
