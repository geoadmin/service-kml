# service-kml

| Branch | Status |
|--------|-----------|
| develop | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoidDZJMHhkcHR5MGNRMmJkSDIzaW5JRUVxWXJtK0d4R25SWFplT3FjMlZNZDNSc21GQ3Ztd0NrbTJCQXhscVIzcU4xcVdEMHRaWDZ2YmZ0M1lseHgwVWJvPSIsIml2UGFyYW1ldGVyU3BlYyI6IjF0d3dwamZtZ2c0MkV0OUIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=develop) |
| master | ![Build Status](https://codebuild.eu-central-1.amazonaws.com/badges?uuid=eyJlbmNyeXB0ZWREYXRhIjoidDZJMHhkcHR5MGNRMmJkSDIzaW5JRUVxWXJtK0d4R25SWFplT3FjMlZNZDNSc21GQ3Ztd0NrbTJCQXhscVIzcU4xcVdEMHRaWDZ2YmZ0M1lseHgwVWJvPSIsIml2UGFyYW1ldGVyU3BlYyI6IjF0d3dwamZtZ2c0MkV0OUIiLCJtYXRlcmlhbFNldFNlcmlhbCI6MX0%3D&branch=master) |

## Table of content

- [Table of content](#table-of-content)
- [Description](#description)
- [Staging Environments](#staging-environments)
- [Versioning](#versioning)
- [Local Development](#local-development)
  - [Make Dependencies](#make-dependencies)
  - [Setting up to work](#setting-up-to-work)
  - [Linting and formatting your work](#linting-and-formatting-your-work)
  - [Test your work](#test-your-work)
    - [Testing with curl](#testing-with-curl)
  - [Docker helpers](#docker-helpers)
- [Deployment](#deployment)
  - [Deployment configuration](#deployment-configuration)

## Description

A Microservice which stores drawings that are created in the mapviewer on s3.
A detailed descriptions of the endpoints can be found in the [OpenAPI Spec](https://github.com/geoadmin/doc-api-specs/blob/develop/public.geo.admin.ch/public.geo.admin.ch.yaml).

## Staging Environments

| Environments | URL                                                                                 |
| ------------ | ----------------------------------------------------------------------------------- |
| DEV          | [https://sys-public.dev.bgdi.ch/api/kml/](https://sys-public.dev.bgdi.ch/api/kml/)  |
| INT          | [https://sys-public.int.bgdi.ch/api/kml/](https://sys-public.int.bgdi.ch/api/kml/)  |
| PROD         | [https://public.geo.admin.ch/api/kml/](https://public.geo.admin.ch/api/kml/)        |

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

If needed create and adapt your local copy of .env.default to your needs.
Afterwards source it (otherwise default values will be used by the service) and
let ENV_FILE point to your local env file:

```bash
cp .env.default .env.local
source .env.local
export ENV_FILE=.env.local
```

Then, you can run the dev target to ensure you have everything needed to develop, test and serve locally

```bash
make dev
```

The other services that are used (DynamoDB local and [MinIO](https://www.min.io) as local S3 replacement) are wrapped in a docker compose.

Starting DynamoDB local and MinIO is done with a simple

```bash
docker-compose up
```

in the source root folder. Make sure to run `make dev` before to ensure the necessary folders `.volumes/*` are in place. These folders are mounted in the services and allow data persistency over restarts of the containers.

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

This serve the application using gunicorn and with the path prefix set to `/api/kml`.

```bash
make dockerrun
```

This will serve the application with the wsgi server, inside a container with the `/api/kml` path prefix.

#### Testing with curl

Here some curl examples 

***Note if you run the server with Flask `make serve` then you need to remove the `/api/kml` path prefix***

```bash
# post a kml
curl -X POST http://localhost:5000/api/kml/admin -F kml="@./tests/samples/valid-kml.xml; type=application/vnd.google-earth.kml+xml" -H "Origin: map.geo.admin.ch"

# get the kml metadata
curl http://localhost:5000/api/kml/admin/${KML_ID} -H "Origin: map.geo.admin.ch"

# update the kml file
curl -X PUT http://localhost:5000/api/kml/admin/${KML_ID} -F admin_id=${ADMIN_ID} -F kml="@./tests/samples/updated-kml.xml; type=application/vnd.google-earth.kml+xml" -H "Origin: map.geo.admin.ch"

# delete the kml
curl -X DELETE http://localhost:5000/api/kml/admin/${KML_ID} -F admin_id=${ADMIN_ID} -H "Origin: map.geo.admin.ch"
```

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

This service is to be deployed to the Kubernetes cluster. See [geoadmin/infra-kubernetes/services/service-kml/README.md](https://github.com/geoadmin/infra-kubernetes/blob/master/services/service-kml/README.md).

### Deployment configuration

The service is configured by Environment Variable:

| Env         | Default               | Description                |
| ----------- | --------------------- | -------------------------- |
| LOGGING_CFG | logging-cfg-local.yml | Logging configuration file |
| AWS_S3_BUCKET_NAME | | AWS S3 bucket name used to save and serve KML files |
| AWS_S3_REGION_NAME | | AWS region name of the S3 service |
| AWS_S3_ENDPOINT_URL | `None` | AWS S3 Endpoint URL. This can be used to use another S3 service as the one from AWS (e.g. local minio) |
| AWS_DB_REGION_NAME | | AWS DynamoDB region name |
| AWS_DB_TABLE_NAME | | AWS DynamoDB table name |
| AWS_DB_ENDPOINT_URL | `None` | AWS DynamoDB Endpoint URL. This can be used to use another DynamoDB service as the one from AWS (e.g. local DynamoDB) |
| KML_STORAGE_HOST_URL | `None` | KML storage host. This can be used if the S3 storage is not on the same host as the service (e.g. local development where service runs on `localhost:5000` and storage on `localhost:9090` |
| KML_MAX_SIZE | `2 * 1024 * 1024` | KML max size file allowed in bytes |
| ALLOWED_DOMAINS | `.*` | Comma separated of domain pattern allowed in Origin header |
| KML_FILE_CACHE_CONTROL | `no-store, max-age=0` | Cache Control header set in answer when serving the KML file. |
| FORWARED_ALLOW_IPS | `*` | Sets the gunicorn `forwarded_allow_ips`. See [Gunicorn Doc](https://docs.gunicorn.org/en/stable/settings.html#forwarded-allow-ips). This setting is required in order to `secure_scheme_headers` to work. |
| FORWARDED_PROTO_HEADER_NAME | `X-Forwarded-Proto` | Sets gunicorn `secure_scheme_headers` parameter to `{${FORWARDED_PROTO_HEADER_NAME}: 'https'}`. This settings is required in order to generate correct URLs in the service responses. See [Gunicorn Doc](https://docs.gunicorn.org/en/stable/settings.html#secure-scheme-headers). |
| SCRIPT_NAME | `''` | If the service is behind a reverse proxy and not served at the root, the route prefix must be set in `SCRIPT_NAME`. |
| CACHE_CONTROL | `no-cache, no-store, must-revalidate` | Cache Control header value of the GET endpoint(s) |
| CACHE_CONTROL_4XX | `public, max-age=3600` | Cache Control header for 4XX responses |
