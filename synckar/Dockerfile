FROM python:3.11-slim

WORKDIR /app

# Copy everything needed for install + runtime
COPY pyproject.toml .
COPY synckar/ synckar/
COPY schema_registry/ schema_registry/
COPY migrations/ migrations/
COPY scripts/ scripts/

# Install the synckar package + all dependencies
RUN pip install --no-cache-dir .

# Generate RSA keys for audit signing (BSA 2023)
RUN python scripts/generate_rsa_keys.py

# Default: run the FastAPI API server
CMD ["uvicorn", "synckar.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
