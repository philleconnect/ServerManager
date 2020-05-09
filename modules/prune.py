#!/usr/bin/env python3

# SchoolConnect Server-Manager - docker prune
# © 2019 Johannes Kreutz.

# Include dependencies
import docker

# Create docker connection
client = docker.from_env()

# Class definition
class prune:
    # Deletes all docker networks with no container connected to it
    @staticmethod
    def networks():
        client.networks.prune()
        
    # Deletes all docker images which are not used by any container
    @staticmethod
    def images():
        client.images.prune()
