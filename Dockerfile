# Multi-stage build with a common base stage and two stages for dev and prod

# ############################
# BASE STAGE
# ############################
FROM python:3.11.6-bookworm as base

# Create a non-root user who owns a directory that will contain all files
ENV SERVICE_NAME=politdocs_assistant_app
RUN adduser --system --group $SERVICE_NAME
RUN mkdir /$SERVICE_NAME
RUN chown $SERVICE_NAME:$SERVICE_NAME /$SERVICE_NAME
WORKDIR /$SERVICE_NAME

# Install poetry
# https://stackoverflow.com/questions/72465421/how-to-use-poetry-with-docker
ENV POETRY_VERSION=1.7.*
ENV POETRY_HOME=/opt/poetry
ENV POETRY_VENV=/opt/poetry-venv
ENV POETRY_CACHE_DIR=/opt/.cache
RUN python3 -m venv $POETRY_VENV \
    && $POETRY_VENV/bin/pip install -U pip setuptools \
    && $POETRY_VENV/bin/pip install poetry==${POETRY_VERSION}
ENV PATH="${POETRY_VENV}/bin:${PATH}"

# Install dependencies for pdf text extraction in german
# https://pypi.org/project/ocrmypdf/
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-deu ghostscript

# Switch to non-root user
USER $SERVICE_NAME

CMD ["bash"]


# ############################
# DEV STAGE
# ############################
FROM base as dev

ENV VERSION="Development"

# Switch to root user for installation
USER root

# Pre-commit hooks
# Create en_US.UTF-8 locale, even though we do not explicitly set LC_ALL here.
# If this is missing we run into issues along the line of
# https://github.com/microsoft/vscode/issues/110491 when pre-commit
# hooks fail when triggered via VScode git UI. This is an unsatisfying fix,
# because I do grasp the underlying problem, but as it does not hurt
# it is good enough for now.
RUN apt-get update && apt-get install -y locales
RUN echo "en_US.UTF-8 UTF-8" > /etc/locale.gen && \
    locale-gen en_US.UTF-8

# Install bc for arbitrary precision arithmetic used
# in the test coverage comparison pre-commit hook.
RUN apt-get update && apt-get install -y bc

# Install python dependencies
WORKDIR /$SERVICE_NAME
COPY ./app/pyproject.toml ./pyproject.toml
COPY ./app/poetry.lock ./poetry.lock
RUN poetry config virtualenvs.create false \
    && poetry install --no-interaction --no-ansi --no-root

# We run dev container as root user instead of USER $SERVICE_NAME
# to allow for file system access. Not great, but for now it is good enough.
USER root

CMD ["bash"]


# ############################
# PROD STAGE
# ############################
FROM base as prod

# Switch to root user for installation
USER root

# Require version as build argument and expose it as environment variable to app and as label
ARG VERSION
RUN ["/bin/bash", "-c", ": ${VERSION:?Build argument VERSION needs to be set and not null.}"]
ENV VERSION=${VERSION}
LABEL com.github.laiskasiili.politdocs_assistant.version=${VERSION}

# Copy source files into image
WORKDIR /$SERVICE_NAME
COPY ./app .

# Install python dependencies
RUN poetry config virtualenvs.create false \
    && poetry install --without dev --no-interaction --no-ansi --no-root

# Switch to non-root user
USER $SERVICE_NAME

CMD ["bash"]
