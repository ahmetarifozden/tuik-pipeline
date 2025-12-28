# Base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.7.1 \
    POETRY_HOME="/opt/poetry" \
    POETRY_VIRTUALENVS_CREATE=false

# Add poetry to path
ENV PATH="$POETRY_HOME/bin:$PATH"

# Install system dependencies
# libpq-dev and gcc are needed for psycopg2 (PostgreSQL adapter)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry using its installer script (recommended)
# or just pip install poetry
RUN pip install "poetry==$POETRY_VERSION"

# Set work directory
WORKDIR /app

# Copy dependencies definition
COPY pyproject.toml poetry.lock ./

# Install dependencies
# --no-root: specific to src layout, we install the project package later or just rely on PYTHONPATH
RUN poetry install --no-interaction --no-ansi --no-root

# Copy project files
COPY . .

# Install the project itself (so imports like src.tuik_pipeline work)
RUN poetry install --no-interaction --no-ansi

# Make shell scripts executable
RUN chmod +x bot.sh run.sh run_config.sh

# Expose API port
EXPOSE 8000

# Default command: Run the API
CMD ["./run.sh"]
