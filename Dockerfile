FROM python:3.12-slim

# System deps for WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 libffi-dev shared-mime-info \
    fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install yt-dlp
RUN pip install --no-cache-dir yt-dlp

# Copy skill files
COPY scripts/ /skill/scripts/
COPY assets/ /skill/assets/

# Install Python deps
RUN pip install --no-cache-dir -r /skill/scripts/requirements.txt

# Working directory (scripts resolve project root from cwd)
WORKDIR /workspace
RUN mkdir -p .git

ENV PYTHONUNBUFFERED=1
