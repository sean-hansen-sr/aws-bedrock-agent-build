FROM python:3.13-slim

# Build time arguments
ARG APP_ENV

# Assign environment variables
ENV APP_ENV=$APP_ENV

WORKDIR /app

CMD ["tail", "-f", "/dev/null"]
