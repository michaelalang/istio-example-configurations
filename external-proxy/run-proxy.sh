#!/bin/bash

podman run -d --rm --replace --name squid-proxy    -p 8080:8080 -p 8443:8443   -v ./certs:/certs:ro,z  squid:latest


#add any user to authenticate with 
#htpasswd htpasswd <username>

#podman run -d --rm --replace --name squid-proxy    -p 8080:8080 -p 8443:8443   -v ./certs:/certs:ro,z \
# -v ./htpasswd:/etc/squid/htpasswd,z -v squid-auth.conf:/etc/squid/squid.conf,z squid:latest
