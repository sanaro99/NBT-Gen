FROM python:3.11-slim

WORKDIR /code

# Copy requirements first to leverage Docker cache
COPY requirements.txt ./

# Install dependencies with cache mount (faster rebuilds)
RUN --mount=type=cache,target=/root/.cache \
    pip install --no-cache-dir -r requirements.txt

# Copy application code, static assets, and templates
COPY app/ /code/app
COPY static/ /code/static
COPY templates/ /code/templates

# Environment variables (adjust as needed)
ENV PYTHONUNBUFFERED=1

# Expose port and start server
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]