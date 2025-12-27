FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Install dependencies from the vulnerable app's requirements
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy the vulnerable app (when building with subfolder as context)
COPY . .

RUN adduser --disabled-password --gecos "" appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Gunicorn entrypoint; module is at /app/app.py after targeted copy
CMD ["sh", "-c", "python database_setup.py && gunicorn -w 3 -b 0.0.0.0:5000 'app:create_app()'"]
