FROM python:3.11-slim

WORKDIR /

# system dependencies (IMPORTANT for docker-in-docker + builds)
RUN apt-get update && apt-get install -y \
    git gcc curl \
    docker.io \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# copy project
COPY . .


# upgrade pip
RUN pip install --upgrade pip

# core dependencies
RUN pip install -r dev-requirements.txt
RUN make build
# IMPORTANT runtime fixes
RUN pip install \
    "uvicorn[standard]" \
    jinja2 \
    docker \
    aiohttp \
    websockets \
    starlette

# environment safety (prevents template issues)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["uvicorn", "livecode_server.server:app", "--host", "0.0.0.0", "--port", "8000"]