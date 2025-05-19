# Dockerfile
FROM python:3.10-slim

# Set environment
WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy app and certs
COPY app /app

# Expose HTTPS port
# EXPOSE 443
EXPOSE 8181

# Run with Gunicorn + Gevent
# CMD ["gunicorn", "ntlm_mock_server:app", \
#      "--certfile=cert.pem", "--keyfile=key.pem", \
#      "--bind=0.0.0.0:443", "--worker-class=gevent", "--workers=1"]
CMD ["gunicorn", "ntlm_mock_server:app", \
     "--bind=0.0.0.0:8181", "--worker-class=gevent", "--workers=1"]