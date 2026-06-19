# Dockerfile for YNAB MCP Connector
# Uses Python 3.13 slim image

FROM python:3.13-slim

WORKDIR /app

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Install runtime dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] pydantic pydantic-settings httpx

# Copy application code
COPY config.py main.py mcp_server.py ynab_client.py api-1.json .

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Switch to non-root user
USER appuser

# Expose port (default from config.py)
EXPOSE 8000

# Run the application
CMD ["python", "main.py"]
