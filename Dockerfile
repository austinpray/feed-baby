FROM python:3.14-slim-trixie as production
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy the project into the image
COPY . /app

# Sync the project into a new environment, asserting the lockfile is up to date
WORKDIR /app
RUN uv sync --locked

CMD ["uv", "run", "server.py"]

FROM production as devcontainer

ARG USERNAME=austinpray
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# install stuff
RUN apt-get update \
 && apt-get install -y --no-install-recommends \
       vim \
       zsh \
       just \
       curl \
       git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Create the user
RUN groupadd --gid $USER_GID $USERNAME \
 && useradd --uid $USER_UID --gid $USER_GID -m $USERNAME --shell /bin/zsh

USER $USERNAME
