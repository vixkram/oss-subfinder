FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    git \
    whois \
    dnsutils \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/backend-requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/backend-requirements.txt && \
    rm -f /tmp/backend-requirements.txt

COPY backend /app/backend

WORKDIR /app/backend

ENV PYTHONPATH="/app/backend" \
    PATH="/app/backend/scripts:${PATH}"

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
