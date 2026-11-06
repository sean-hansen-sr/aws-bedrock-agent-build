FROM python:3.13-slim

# Build time arguments
ARG APP_ENV
ARG APP_MODEL_ID
ARG APP_AWS_REGION
ARG APP_AGENT_TABLE_NAME

# Assign environment variables
ENV APP_ENV=$APP_ENV
ENV MODEL_ID=$APP_MODEL_ID
ENV AWS_REGION=$APP_AWS_REGION
ENV AGENT_TABLE_NAME=$APP_AGENT_TABLE_NAME
# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Expose port 8080 to the outside world
EXPOSE 8080

# Run the FastAPI application when the container starts
#CMD ["python", "agent.py"]
CMD ["uvicorn", "agent:app", "--host", "0.0.0.0"]
