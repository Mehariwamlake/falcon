FROM python:3.11-slim

WORKDIR /app

# system deps
RUN apt-get update && apt-get install -y \
    git gcc curl \
    && rm -rf /var/lib/apt/lists/*

# install dependencies
COPY . .

RUN pip install --upgrade pip
RUN pip install -r dev-requirements.txt
RUN pip install "uvicorn[standard]"
RUN pip install jinja2

EXPOSE 8000

CMD ["uvicorn", "livecode_server.server:app", "--host", "0.0.0.0", "--port", "8000"]
