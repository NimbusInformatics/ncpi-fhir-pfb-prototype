#!/usr/bin/env bash

docker exec -it `docker ps | grep ncpi-fhir-pfb-prototype | awk '{print $1}'` /bin/bash
