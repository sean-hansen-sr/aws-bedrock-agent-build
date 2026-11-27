FROM python:3.13-slim

ARG APP_ENV
ARG APP_MODEL_ID
ARG APP_AWS_REGION
ARG APP_AGENT_TABLE_NAME
ARG APP_KNOWLEDGE_BASE_ID
ARG APP_DATA_SOURCE_ID
ARG APP_DATA_SOURCE_BUCKET
ARG APP_SEED_KNOWLEDGE_PATH

ENV APP_ENV=$APP_ENV
ENV MODEL_ID=$APP_MODEL_ID
ENV AWS_REGION=$APP_AWS_REGION
ENV AGENT_TABLE_NAME=$APP_AGENT_TABLE_NAME
ENV KNOWLEDGE_BASE_ID=$APP_KNOWLEDGE_BASE_ID
ENV DATA_SOURCE_ID=$APP_DATA_SOURCE_ID
ENV DATA_SOURCE_BUCKET=$APP_DATA_SOURCE_BUCKET
ENV SEED_KNOWLEDGE_PATH=$APP_SEED_KNOWLEDGE_PATH

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN adduser --disabled-password --gecos "" appuser && \
    chown -R appuser:appuser /app

USER appuser

ENV PORT=8080
ENV PATH="/home/appuser/.local/bin:${PATH}"

EXPOSE $PORT

CMD ["python3", "-m", "uvicorn", "agent:app", "--host", "0.0.0.0", "--port", "8080"]
