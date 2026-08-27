FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml README.md ./
COPY services ./services
COPY data ./data
RUN pip install --no-cache-dir -e .
CMD ["python", "-m", "services.processor.transcode"]
