FROM python:3.11-slim

WORKDIR /app

# Install system packages
RUN apt-get update && apt-get install -y \
    git \
    gcc \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files first (better layer caching)
COPY dev-requirements.txt .
COPY requirements.txt* ./

# Upgrade pip
RUN pip install --upgrade pip

# Install Python dependencies
RUN pip install -r dev-requirements.txt

# Runtime dependencies
RUN pip install \
    "uvicorn[standard]" \
    docker \
    aiohttp \
    websockets \
    jinja2 \
    starlette \
    starlette==0.27.0 \
    jinja2==3.1.2

# Copy application
COPY . .

ENV PYTHONUNBUFFERED=1
ENV LIVECODE_PORT=8010

EXPOSE 8010

CMD ["uvicorn", "livecode_server.server:app", "--host", "0.0.0.0", "--port", "8010"]