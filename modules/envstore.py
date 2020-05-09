#!/usr/bin/env python3

# SchoolConnect Server-Manager - environment variable management class
# © 2019 Johannes Kreutz.

# Include dependencies
import os
import json
import socket

# Include modules
import config

# Class definition
class envman:
    def __init__(self):
        if not os.path.exists(config.configpath + "env.json"):
            self.__storage = {}
            self.write()
        self.updateLocalIp()

    # Read stored environment variables and their descriptions from configuration files
    def load(self):
        envfile = open(config.configpath + "env.json", "r")
        self.__storage = json.loads(envfile.read())
        envfile.close()

    # Writes actual environment variables and their descriptions to the storage files
    def write(self):
        envfile = open(config.configpath + "env.json", "w")
        envfile.write(json.dumps(self.__storage))
        envfile.close()

    # Returns the value of an environment variable with the given id if available
    def getValue(self, id):
        self.load()
        if id in self.__storage:
            return self.__storage[id]["value"]
        else:
            return False

    # Returns the description of an environment variable with the given id if available
    def getDescription(self, id):
        self.load()
        if id in self.__storage:
            return self.__storage[id]["description"]
        else:
            return False

    # Returns the mutability of an environment variable with the given id
    def isMutable(self, id):
        self.load()
        if id in self.__storage:
            return self.__storage[id]["mutable"]
        else:
            return False

    # Returns all environment variables as json
    def getJson(self):
        return json.dumps(self.__storage)

    # Stores a new environment variable
    def storeValue(self, id, value, description = None, mutable = False):
        self.load()
        description = "" if description == None else description
        entry = {"value":value,"description":description,"mutable":mutable}
        self.__storage[id] = entry
        self.write()

    # Returns true if a environment variable for a given id exists
    def doesKeyExist(self, id):
        self.load()
        return id in self.__storage

    # Updates the environment variable storing the hosts IP address
    def updateLocalIp(self):
        self.load()
        self.storeValue("HOST_NETWORK_ADDRESS", self.getLocalIp(), "Die lokale IP-Addresse des Hostsystems.")
        self.write()

    # Helper function to get local machine ip on the default interface
    def getLocalIp(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # doesn't even have to be reachable
            s.connect(('10.255.255.255', 1))
            IP = s.getsockname()[0]
        except:
            IP = '127.0.0.1'
        finally:
            s.close()
        return IP
