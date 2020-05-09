#!/usr/bin/env python3

# SchoolConnect Server-Manager - service description class
# © 2019 Johannes Kreutz.

# Include dependencies
import json
import urllib.request
import os

# Include modules
import config
import modules.repository as repo
import modules.filesystem as fs

# Manager objects
repo = repo.repository()

# Class definition
class serviceDescription:
    def __init__(self, firstsetup, name, version, url = ""):
        self.__name = name
        self.__version = version
        if firstsetup:
            self.loadDescriptionFile(self.__version)
        else:
            self.readDescriptionFile()

    # FILE MANAGEMENT
    # Loads a description file
    def loadDescriptionFile(self, version):
        url = repo.getUrl(self.__name, version)
        fs.filesystem.removeElement(config.servicepath + self.__name + "/service_" + version + ".json")
        urllib.request.urlretrieve(url, config.servicepath + self.__name + "/service_" + version + ".json")
        self.__version = version
        self.readDescriptionFile()

    # Reads a locally stored service file
    def readDescriptionFile(self):
        serviceFile = open(config.servicepath + self.__name + "/service_" + self.__version + ".json", "r")
        self.__desc = json.loads(serviceFile.read())
        serviceFile.close()

    # Reload service description
    def checkForUpdate(self):
        latest = repo.getLatestCompatible(self.__name, self.__version)
        if repo.compareVersions(latest, self.__version) > 0:
            return latest
        return False

    # Runs an update
    def executeUpdate(self, version):
        oldVersion = self.__version
        self.loadDescriptionFile(version)
        self.removeOldFile(oldVersion)

    # Removes an old locally stored file version
    def removeOldFile(self, version):
        os.remove(config.servicepath + self.__name + "/service_" + version + ".json")

    # VALUE GETTERS
    # Returns a list of all containers
    def getContainers(self):
        list = []
        for container in self.__desc["containers"]:
            list.append(container["name"])
        return list

    # Returns the number of containers
    def getContainerCount(self):
        return len(self.getContainers())

    # Returns a container description for the given name
    def getContainerObject(self, name):
        for container in self.__desc["containers"]:
            if container["name"] == name:
                return container
        return False

    # Returns an array of all defined networks
    def getNetworks(self):
        return self.__desc["networks"]

    # Returns an array of all defined volumes
    def getVolumes(self):
        return self.__desc["volumes"]

    # Returns an array of all defined environment variables
    def getEnvironment(self):
        return self.__desc["environment"]

    # Get image source
    def getImageSource(self, name):
        response = {}
        container = self.getContainerObject(name)
        if "prebuilt" in container:
            response["prebuilt"] = container["prebuilt"]
        else:
            response["url"] = container["url"]
        return response
