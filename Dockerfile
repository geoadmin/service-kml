FROM python:3.11-slim-bookworm AS base

ENV USER=geoadmin
ENV GROUP=geoadmin
ENV INSTALL_DIR=/opt/service-kml
ENV SRC_DIR=/usr/local/src/service-kml
ENV PIPENV_VENV_IN_PROJECT=1

RUN groupadd -r ${GROUP} && useradd -r -s /bin/false -g ${GROUP} ${USER} \
     && mkdir -p ${INSTALL_DIR}/app && chown ${USER}:${GROUP} ${INSTALL_DIR}/app

###########################################################
# Builder container
FROM base AS builder

RUN pip3 install pipenv \
    && pipenv --version \
    && mkdir -p ${SRC_DIR} && chown ${USER}:${GROUP} ${SRC_DIR}

COPY Pipfile.lock ${SRC_DIR}
RUN cd ${SRC_DIR} && pipenv sync

COPY --chown=${USER}:${GROUP} app ${INSTALL_DIR}/app
COPY --chown=${USER}:${GROUP} wsgi.py ${INSTALL_DIR}/

###########################################################
# Container to use in production
FROM base AS production

# Activate virtual environnment
ENV VIRTUAL_ENV=${INSTALL_DIR}/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONHOME=""

ARG GIT_HASH=unknown
ARG GIT_BRANCH=unknown
ARG GIT_DIRTY=""
ARG VERSION=unknown
ARG AUTHOR=unknown
ARG HTTP_PORT=5000
LABEL git.hash=$GIT_HASH
LABEL git.branch=$GIT_BRANCH
LABEL git.dirty="$GIT_DIRTY"
LABEL version=$VERSION
LABEL author=$AUTHOR

# Install venv and app from builder stage
COPY --from=builder ${SRC_DIR}/.venv/ ${INSTALL_DIR}/.venv/
COPY --from=builder ${INSTALL_DIR}/ ${INSTALL_DIR}/

# Overwrite the version.py from source with the actual version
RUN echo "APP_VERSION = '$VERSION'" > ${INSTALL_DIR}/app/version.py

WORKDIR ${INSTALL_DIR}
USER ${USER}

EXPOSE ${HTTP_PORT}

# Use a real WSGI server
ENTRYPOINT ["python3", "wsgi.py"]
