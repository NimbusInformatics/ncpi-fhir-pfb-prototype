# ncpi-fhir-pfb-prototype

## About

This is a simple Docker-based environment for developing a FHIR->PFB
service. The idea is to have a webservice that can act as a proxy
for a given FHIR server.  Searches can go through this proxy services
and the FHIR server's response will be aggregated and converted to
PFB for use in workspace environments that understand PFB, such as
[Terra](https://app.terra.bio).  

For now we have a standalone Python script that will connect with a
FHIR server (namely the FHIR server on Google that Nimbus is using to
test load synthetic COVID data) and do a conversion to a PFB.

## TODO Items

See the Technical Guidelines [doc](https://docs.google.com/document/d/1lHiIDjJDJih131-Q7mVu7zlInfDKs8_a-71pwJ68sfs/edit#) from NCPI, we'll do design work there and link to GitHub issues where it makes sense.

## Origin

The Docker compose configuration and coding environment is
inspired by, and forked from, this blog post:

**🐳 Simplified guide to using Docker for local development environment**

_The blog link :_

[https://blog.atulr.com/docker-local-environment/](https://blog.atulr.com/docker-local-environment/)

## Running the Docker Container as a Dev Environment

To run the example:

- `git clone https://github.com/NimbusInformatics/ncpi-fhir-pfb-prototype.git`
- `docker-compose up`
- or `docker-compose up -d` if you want to avoid console output
- or `docker-compose up --build` if you want to force rebuilding of the Docker image

Details about each service and how to run them is present in the individual services directories.

## Connecting to Python Dev Environment

Once you launch with `docker-compose up` you can login in to the Python service
container using:

```
# connect from your host machine
$> ./connect.sh

now within the container I'm running as root and in the ~/py1 directory
# which is the directory containing the flask app
root@02d2b8fce3af:~/py1# whoami
root

# now if I go to ~/py-dev it contains the working directory with my scripts
root@02d2b8fce3af:~# cd ~/py-dev/
root@02d2b8fce3af:~/py-dev# ls
scripts
```

## Code Organization

I've reorganized the services into the `services` directory and the
`working` directory contains the scripts and is mounted and shared across the docker containers when run.

## FHIR -> PFB Python Script

Eventually this will be made into a service running on the sample Python server
below.  But for now we're working on a FHIR->PFB script.  It's located in
`working/scripts`.  You can run it with the following command _from within the python dev environment you connected to above_.  
Make sure you replace the FHIR server URL with a valid server:

_See the instructions below for logging in and setting up your Google cloud credentials_.

```
%> python3 fhir_pfb_export.py https://healthcare.googleapis.com/v1/projects/nimbus-fhir-test/locations/us-west2/datasets/nimbus-fhir-dataset/fhirStores/nimbus-fhir-store/fhir  $(gcloud auth application-default print-access-token) covid
```

## Make a new PFB Schema

You do this if you need to modify the schema of the PFB.

```
%> pfb from -o minimal_schema.avro dict minimal_file.json
```

## Python Version

See the [official python images](https://hub.docker.com/_/python) on DockerHub
as well as the [releases of Debian](https://wiki.debian.org/DebianReleases).  I'm
using Debian Buster and Python 3 as the basis for the Python environment that gets
launched:

    python:3-buster

It's probably a good idea to use a specific version number of Python when
writing real scripts/services.

## Basic Python Server

The flask server is running on `http://localhost:9000` and just returns "Hello from py1"

This will eventually be the place where we can prototype the FHIR to PFB proxy
service.

## Working with a Google FHIR Server

So far our prototyping has been on the Google FHIR server.  To use this server
you need to 1) setup/login to your service account in the Docker container
and 2) give that service account (or your primary account) access to the FHIR
server running on Google.

### Setup Google Cloud SDK Using Service Account

Once you've logged into the Docker container that you'll use as your dev environment
you need to run:

```
%> gcloud init
```

That will walk you through authorizing your SDK with whatever google cloud
account and project you want to use.

You may need to then setup a service account running on this container:

```
%> gcloud iam service-accounts create boconnor-service-account-1
Created service account [boconnor-service-account-1].

%> gcloud projects add-iam-policy-binding my-project --member="serviceAccount:boconnor-service-account-1@my-project.iam.gserviceaccount.com" --role="roles/owner"

%> mkdir ~/.keys

%> gcloud iam service-accounts keys create ~/.keys/boconnor-service-account-1.json --iam-account=boconnor-service-account-1@my-project.iam.gserviceaccount.com
```

You can see the [google cloud docs](https://cloud.google.com/docs/authentication/production)
for more information on this process.

You need to add that service account to the permissions on your FHIR server.

### Setup Google Cloud SDK without Service Account

I just did the following:

```
%> gcloud auth application-default login
```

And that wrote a file with my credentials: `/root/.config/gcloud/application_default_credentials.json`

## Loading a PFB Into Terra

Now that you've generated a PFB how do you use it in the Terra environment?

You need to:

1) host the PFB file on a google bucket
2) load the PFB in Terra using https://app.terra.bio/#import-data?format=PFB&url=https://storage.googleapis.com/dsp-pi-boconnor-dev/20201105_pfb_testing/minimal_data.pfb
