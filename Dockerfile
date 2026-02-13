# Multi-stage build for smaller image
FROM python:3.11-slim as builder

WORKDIR /build
COPY pyproject.toml .
COPY src/ ./src/
RUN pip install --user --no-cache-dir .

# Runtime stage
FROM python:3.11-slim

# Copy Python packages from builder to a location accessible by all users
COPY --from=builder /root/.local /usr/local
ENV PATH=/usr/local/bin:$PATH
ENV PYTHONPATH=/usr/local/lib/python3.11/site-packages:$PYTHONPATH

# Copy application code
WORKDIR /app
COPY src/ /app/src/

# Create cache directory for models
RUN mkdir -p /tmp/transformers_cache && chmod 777 /tmp/transformers_cache
ENV TRANSFORMERS_CACHE=/tmp/transformers_cache
ENV HF_HOME=/tmp/transformers_cache

# Pre-download models to avoid startup delay
# Embedding model (~100MB) and cross-encoder reranking model (~80MB)
RUN python -c "from sentence_transformers import SentenceTransformer, CrossEncoder; SentenceTransformer('all-MiniLM-L6-v2'); CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')"

# Run as non-root for security
USER nobody

# Entry point
CMD ["python", "-m", "src.faqbot.main"]
