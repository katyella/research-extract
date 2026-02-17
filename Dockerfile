FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends yt-dlp poppler-utils curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /skill
COPY scripts/ scripts/

CMD ["python3", "scripts/test_pipeline.py"]
