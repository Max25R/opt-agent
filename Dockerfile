# The demo (src/opt_agent/demo/), as one image.
#   docker build -t opt-agent .
#   docker run --rm -p 8000:8000 opt-agent                                   # examples mode, no key
#   docker run --rm -p 8000:8000 --env-file .env -e OPT_AGENT_LIVE=1 opt-agent   # live mode
# .env never enters the image (.dockerignore): --env-file passes the key at run time only.
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# The locked versions first, in their own layer, so a code change doesn't reinstall them.
COPY requirements.lock ./
RUN pip install -r requirements.lock

# Then the package itself (with the demo's page and cached replies), resolving nothing.
COPY pyproject.toml README.md LICENSE ./
COPY src ./src
RUN pip install --no-deps .

# Not root. Live mode writes its spend ledger, call log and replies under /app/logs.
RUN useradd --create-home demo && mkdir -p /app/logs && chown demo /app/logs
USER demo

EXPOSE 8000
CMD ["python", "-m", "opt_agent.demo", "--host", "0.0.0.0", "--port", "8000"]
