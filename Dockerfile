FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
COPY README.md .
COPY src/ ./src/
COPY tests/ ./tests/

RUN pip install -e ".[dev]"

CMD ["pytest"]