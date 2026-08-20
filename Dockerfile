FROM python:3.12-slim

# Copy the uv binary directly from Astral's distroless image - this is the
# officially recommended way to get uv into a Docker image (much faster
# than `pip install uv`, and avoids pulling pip's own resolver in just to
# install a different resolver).
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /usr/local/bin/

# Prevent .pyc files and force stdout/stderr to be unbuffered (so logs show
# up immediately in `docker-compose logs`).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy

WORKDIR /app

COPY requirements.txt .

# --system installs into the normal Python environment (not a separate venv)
# so `uvicorn ...` below finds everything exactly as it did with plain pip -
# just faster. (A separate `uv run` at CMD time was removed: without a
# pyproject.toml in this image, it depended on version-specific fallback
# behavior instead of a defined contract - simplest to just not need it.)
RUN uv pip install --system --no-cache -r requirements.txt

COPY app ./app

COPY src ./src
COPY config ./config
RUN uv pip install --no-cache-dir -e .

ENTRYPOINT ["benchmark"]
CMD ["--help"]
