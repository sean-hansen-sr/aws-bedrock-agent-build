FROM python:3.13-slim

# Build time arguments
ARG APP_ENV

# Assign environment variables
ENV APP_ENV=$APP_ENV
# Prevent Python from writing .pyc files and enable unbuffered logging
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . /app

# Expose port 80 to the outside world
EXPOSE 80

# Run the FastAPI application when the container starts
CMD ["python", "main.py"]