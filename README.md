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
  - [Docker helpers](#docker-helpers)
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
```bash
git clone git@github.com:geoadmin/service-kml
```

create and adapt your local copy of .env.default to your needs.
Afterwards source it (otherwise default values will be used by the service) and
let ENV_FILE point to your local env file:
```bash
cp .env.default .env.local
source .env.local
export ENV_FILE=.env.local
```

Then, you can run the setup target to ensure you have everything needed to develop, test and serve locally
```bash
make setup
```

That's it, you're ready to work.
### Linting and formatting your work
In order to have a consistent code style the code should be formatted using `yapf`. Also to avoid syntax errors and non
pythonic idioms code, the project uses the `pylint` linter. Both formatting and linter can be manually run using the
following command:
```bash
make format-lint
```
**Formatting and linting should be at best integrated inside the IDE, for this look at
[Integrate yapf and pylint into IDE](https://github.com/geoadmin/doc-guidelines/blob/master/PYTHON.md#yapf-and-pylint-ide-integration)**
### Test your work
Testing if what you developed work is made simple. You have four targets at your disposal. **test, serve, gunicornserve, dockerrun**
```bash
make test
```
This command run the integration and unit tests.
```bash
make serve
```
This will serve the application through Flask without any wsgi in front.
```bash
make gunicornserve
```
This will serve the application with the Gunicorn layer in front of the application
```bash
make dockerrun
```
This will serve the application with the wsgi server, inside a container.
To stop serving through containers,
```bash
make shutdown
```
Is the command you're looking for.
### Docker helpers

From each github PR that is merged into `master` or into `develop`, one Docker image is built and pushed on AWS ECR with the following tag:

- `vX.X.X` for tags on master
- `vX.X.X-beta.X` for tags on develop 

Each image contains the following metadata:

- author
- git.branch
- git.hash
- git.dirty
- version

These metadata can be read with the following command

```bash
# NOTE: Currently we don't have permission to do docker pull on AWS ECR
make dockerlogin
docker pull 974517877189.dkr.ecr.eu-central-1.amazonaws.com/service-kml:develop.latest

# NOTE: jq is only used for pretty printing the json output,
# you can install it with `apt install jq` or simply enter the command without it
docker image inspect --format='{{json .Config.Labels}}' 974517877189.dkr.ecr.eu-central-1.amazonaws.com/service-kml:develop.latest | jq
```

You can also check these metadata on a running container as follows

```bash
docker ps --format="table {{.ID}}\t{{.Image}}\t{{.Labels}}"
```

To build a local docker image tagged as `service-kml:local-${USER}-${GIT_HASH_SHORT}` you can
use

```bash
make dockerbuild
```

To push the image on the ECR repository use the following two commands

```bash
make dockerlogin
make dockerpush
```


## Deployment

This service is to be deployed to the Kubernetes cluster once it is merged.
TO DO: give instructions to deploy to kubernetes.
### Deployment configuration

The service is configured by Environment Variable:

| Env         | Default               | Description                |
| ----------- | --------------------- | -------------------------- |
| LOGGING_CFG | logging-cfg-local.yml | Logging configuration file |
