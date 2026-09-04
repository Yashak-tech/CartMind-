FROM python:3.11-slim

# Create a non-root user with UID 1000 (Hugging Face Spaces requirement)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONPATH=/app \
    PORT=7860

WORKDIR /app

# Install Python dependencies
COPY --chown=user requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

# Copy application source into /app/backend to preserve 'backend.*' package imports
COPY --chown=user . /app/backend/

# Expose default Hugging Face Spaces port
EXPOSE 7860

# Start FastAPI application listening on 0.0.0.0:7860
CMD ["sh", "-c", "uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-7860}"]
