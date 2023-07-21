# Fractal Finance HTTP API 🚲💨🕸️

[![Latest tag](https://github.com/FractalFI/api/actions/workflows/tag-ci.yml/badge.svg)](https://github.com/FractalFI/api/actions/workflows/tag-ci.yml)

Fractal Finance HTTP API is used by our app to fetch tokens and liquidity
pool pairs.

Please make sure you have [Docker](https://docs.docker.com/install/) first.

Next, make a copy of the `env.example` file, and update the relevant variables.

Finally, to start the services run:

    docker compose up

This will start three services:
- `api`: the backend
- `sync`: the service that is constantly syncing information on pairs from the chain
- A redis instance

## Running locally
This project is set up with [`poetry`](https://python-poetry.org/docs/) and Python 3.9.14. We recommend installing
[`pyenv`](https://github.com/pyenv/pyenv) to easily manage different Python versions.

**Note**: Make sure you update your `.env` file to point to localhost (i.e: redis url)

Installing dependencies:

    poetry install

Running the API (after the previous command)

    api-start

Running the syncing process (needed for scraping data from the chain)

    api-sync

This will spawn and use a virtual environment in `.venv` and install the dependencies defined in `poetry.lock`
(or `pyproject.toml`) if the lock file was missing (which should not happen).

When adding new dependencies, one should run:

    poetry add package@version
