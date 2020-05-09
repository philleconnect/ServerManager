#!/usr/bin/env python3

# SchoolConnect Server-Manager - network class
# © 2019 Johannes Kreutz.

# Include dependencies
import docker

# Create docker connection
client = docker.from_env()

# Class definition
class network:
    def __init__(self, exists, id, name, internal):
        if exists:
            try:
                self.__network = client.networks.get(network_id=id)
            except docker.errors.NotFound:
                print("Network lookup error. No network with the given id existing.")
            except docker.errors.APIError:
                print("Didn't expect to get here. Figure out why this code ran.")
        else:
            try:
                self.__network = client.networks.create(name=name, driver="bridge", check_duplicate=True, internal=internal)
            except docker.errors.APIError:
                print("Network creation error. Check inputs.")

    # Returns the name of this network
    def getName(self):
        return self.__network.name

    # Returns the id of this network
    def getId(self):
        return self.__network.id

    # Connects this networo to the container with the given id
    def connect(self, id, aliases):
        self.__network.connect(container=id, aliases=aliases)
