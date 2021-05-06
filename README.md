# service-kml

| Branch | Status |
|--------|-----------|
| develop | ![Build Status](<codebuild-badge>) |
| master | ![Build Status](<codebuild-badge>) |

## Table of content

- [Table of content](#table-of-content)
- [Description](#description)
  - [Staging Environments](#staging-environments)
  - [POST](#post)
  - [GET](#get)
  - [PUT](#put)
- [Versioning](#versioning)
- [Local Development](#local-development)
  - [Make Dependencies](#make-dependencies)
  - [Setting up to work](#setting-up-to-work)
  - [Linting and formatting your work](#linting-and-formatting-your-work)
  - [Test your work](#test-your-work)
- [Docker](#docker)
- [Deployment](#deployment)
  - [Deployment configuration](#deployment-configuration)

## Description

A Microservice which stores drawings that are created in the mapviewer on s3.
A detailed descriptions of the endpoints can be found in the [OpenAPI Spec](openapi.yaml).

### Staging Environments

This service has three endpoints:

- POST/kml
- GET/kml/{id}
- PUT/kml/{id}

| Environments | URL                                                                                                                   |
| ------------ | --------------------------------------------------------------------------------------------------------------------- |
| DEV          | [https://service-kml.bgdi-dev.swisstopo.cloud/v4/name/](https://service-kml.bgdi-dev.swisstopo.cloud/v4/name/)  |
| INT          | [https://service-kml.bgdi-int.swisstopo.cloud/v4/name/](https://service-kml.bgdi-int.swisstopo.cloud/v4/name/)  |
| PROD         | [https://service-kml.bgdi-prod.swisstopo.cloud/v4/name/](https://service-kml.bgdi-int.swisstopo.cloud/v4/name/) |

### POST

Payload is the kml drawn in the map.

| Path | Method | Content Type | Refer | Response Type|
|------|--------|--------------|-------|--------------|
| | POST | application/vnd.google-earth.kml+xml | map.geo.admin.ch, .bgdi.ch | application/json |

### GET

| Path | Method | Response Type|
|------|--------|--------------|
| | GET | application/vnd.google-earth.kml+xml |

### PUT

Payload is the kml to update.

| Path | Method | Content Type | Refer | Response Type|
|------|--------|--------------|-------|--------------|
| | PUT | application/vnd.google-earth.kml+xml | map.geo.admin.ch, .bgdi.ch | application/json |

## Versioning

This service uses [SemVer](https://semver.org/) as versioning scheme. The versioning is automatically handled by `.github/workflows/main.yml` file.

See also [Git Flow - Versioning](https://github.com/geoadmin/doc-guidelines/blob/master/GIT_FLOW.md#versioning) for more information on the versioning guidelines.

## Local Development

### Make Dependencies

The **Make** targets assume you have **python3.7**, **pipenv**, **bash**, **curl**, **tar**, **docker** and **docker-compose** installed.

### Setting up to work

First, you'll need to clone the repo
    git clone git@github.com:geoadmin/service-kml
Then, you can run the setup target to ensure you have everything needed to develop, test and serve locally
    make setup
That's it, you're ready to work.
### Linting and formatting your work
In order to have a consistent code style the code should be formatted using `yapf`. Also to avoid syntax errors and non
pythonic idioms code, the project uses the `pylint` linter. Both formatting and linter can be manually run using the
following command:
    make format-lint
**Formatting and linting should be at best integrated inside the IDE, for this look at
[Integrate yapf and pylint into IDE](https://github.com/geoadmin/doc-guidelines/blob/master/PYTHON.md#yapf-and-pylint-ide-integration)**
### Test your work
Testing if what you developed work is made simple. You have four targets at your disposal. **test, serve, gunicornserve, dockerrun**
    make test
This command run the integration and unit tests.
    make serve
This will serve the application through Flask without any wsgi in front.

    make gunicornserve

This will serve the application with the Gunicorn layer in front of the application

    make dockerrun

This will serve the application with the wsgi server, inside a container.
To stop serving through containers,

    make shutdown

Is the command you're looking for.

## Docker

The service is encapsulated in a Docker image. Images are pushed on the public [Dockerhub](https://hub.docker.com/r/swisstopo/service-kml/tags) registry. From each github PR that is merged into develop branch, one Docker image is built and pushed with the following tags:

- `develop.latest`
- `CURRENT_VERSION-beta.INCREMENTAL_NUMBER`

From each github PR that is merged into master, one Docker image is built an pushed with the following tag:

- `VERSION`

Each image contains the following metadata:

- author
- git.branch
- git.hash
- git.dirty
- version

These metadata can be seen directly on the dockerhub registry in the image layers or can be read with the following command

```bash
# NOTE: jq is only used for pretty printing the json output,
# you can install it with `apt install jq` or simply enter the command without it
docker image inspect --format='{{json .Config.Labels}}' swisstopo/service-kml:develop.latest | jq
```

You can also check these metadata on a running container as follows

```bash
docker ps --format="table {{.ID}}\t{{.Image}}\t{{.Labels}}"
```

## Deployment

This service is to be deployed to the Kubernetes cluster once it is merged.
TO DO: give instructions to deploy to kubernetes.
### Deployment configuration

The service is configured by Environment Variable:

| Env         | Default               | Description                |
| ----------- | --------------------- | -------------------------- |
| LOGGING_CFG | logging-cfg-local.yml | Logging configuration file |