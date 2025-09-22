FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libffi-dev \
    git \
    whois \
    dnsutils \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && \
    pip install --no-cache-dir -r /tmp/requirements.txt

COPY backend /app
COPY backend/start.sh /app/start.sh

RUN chmod +x /app/start.sh

WORKDIR /app

ENV PATH="/app/scripts:${PATH}"

EXPOSE 8000

CMD ["/app/start.sh"]
