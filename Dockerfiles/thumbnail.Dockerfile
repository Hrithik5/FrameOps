FROM python:3.11-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY services ./services
COPY data ./data
RUN pip install --no-cache-dir pillow pypdf pydantic
CMD ["python", "-m", "services.processor.thumbnail"]
