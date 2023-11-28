# Base stage
FROM pypy:3.9-slim AS base

ENV POETRY_HOME=/etc/poetry
ENV POETRY_VIRTUALENVS_CREATE=false

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc g++ libssl-dev libev-dev curl && \
    apt-get clean

RUN pip install poetry

ENV PATH="$PATH:$POETRY_HOME/bin"

# Prod stage
FROM base AS prod

WORKDIR /app
COPY ./ /app/
RUN poetry install 
EXPOSE 8000
ENTRYPOINT ["poetry", "run", "api-start"]

# Sync stage
FROM base AS sync

WORKDIR /app
COPY ./ /app/
RUN poetry install 
EXPOSE 8000
ENTRYPOINT ["poetry", "run", "api-sync"]
