FROM python:3.11-slim

WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./

# Install dependencies with cache mount (faster rebuilds)
RUN --mount=type=cache,target=/root/.cache \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the app
COPY . /app

# Environment variables (adjust as needed)
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

# Run Uvicorn (assuming FastAPI)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]