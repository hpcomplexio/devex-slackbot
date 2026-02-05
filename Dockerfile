# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /build
COPY pyproject.toml .
RUN pip install --user --no-cache-dir -e .

# Runtime stage
FROM python:3.11-slim

# Copy Python packages from builder
COPY --from=builder /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

# Copy application code
WORKDIR /app
COPY src/ /app/src/

# Pre-download embedding model to avoid startup delay
# This downloads ~100MB sentence-transformers model during build
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Run as non-root for security
USER nobody

# Entry point
CMD ["python", "-m", "src.faqbot.main"]
