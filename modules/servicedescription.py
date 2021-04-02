#!/usr/bin/env python3

# SchoolConnect Server-Manager - service description class
# © 2019 - 2021 Johannes Kreutz.

# Include dependencies
import json
import urllib.request
import os
import yaml

# Include modules
import config
import modules.repository as repo
import modules.filesystem as fs
from modules.envparser import envParser

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
            if os.path.exists(config.servicepath + self.__name + "/docker-compose.yml"):
                self.dockerComposeFile = True
            else:
                self.dockerComposeFile = False
            self.readDescriptionFile()

    # FILE MANAGEMENT
    # Loads a description file
    def loadDescriptionFile(self, version):
        url = repo.getUrl(self.__name, version)
        if url.endswith(".json"):
            self.dockerComposeFile = False
            localPath = config.servicepath + self.__name + "/service_" + version + ".json"
        else:
            self.dockerComposeFile = True
            localPath = config.servicepath + self.__name + "/docker-compose.yml"
        fs.filesystem.removeElement(localPath)
        urllib.request.urlretrieve(url, localPath)
        self.__version = version
        if self.dockerComposeFile:
            envUrl = url.replace("docker-compose.yml", "settings.env.default")
            fs.filesystem.removeElement(config.servicepath + self.__name + "/settings.env.default")
            urllib.request.urlretrieve(envUrl, config.servicepath + self.__name + "/settings.env.default")
        self.readDescriptionFile()

    # Reads a locally stored service file
    def readDescriptionFile(self):
        if self.dockerComposeFile:
            with open(config.servicepath + self.__name + "/docker-compose.yml", "r") as serviceFile:
                self.__desc = yaml.safe_load(serviceFile.read())
            with open(config.servicepath + self.__name + "/settings.env.default", "r") as envFile:
                # TODO: Parse env file
                return
        else:
            with open(config.servicepath + self.__name + "/service_" + self.__version + ".json", "r") as serviceFile:
                self.__desc = json.loads(serviceFile.read())

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
        if self.dockerComposeFile:
            os.remove(config.servicepath + self.__name + "/docker-compose.yml")
            os.remove(config.servicepath + self.__name + "/settings.env.default")
        else:
            os.remove(config.servicepath + self.__name + "/service_" + version + ".json")

    # VALUE GETTERS
    # Returns a list of all containers
    def getContainers(self):
        list = []
        if self.dockerComposeFile:
            for name, container in self.__desc["services"].items():
                c = {
                    "name": name,
                    "hostname": name,
                    "ports": [],
                    "networks": [],
                    "volumes": [],
                    "environment": []
                }
                # Translate image source
                if "image" in container:
                    source = container["image"]
                    if ":" in source:
                        parts = source.split(":")
                        c["prebuilt"] = {
                            "name": parts[0],
                            "version": parts[1],
                        }
                    else:
                        c["prebuilt"] = {
                            "name": container["image"],
                            "version": "latest",
                        }
                else:
                    c["url"] = repo.getUrl(self.__name, version).replace("docker-compose.yml", name + ".tar.gz")
                # Translate ports
                for port in container["ports"]:
                    parts = port.split(":")
                    c["ports"].append({
                        "external": parts[0],
                        "internal": parts[1],
                    })
                # Translate networks
                for network in container["networks"]:
                    c["networks"].append({
                        "name": network,
                    })
                # Translate volumes
                for volume in container["volumes"]:
                    parts = volume.split(":")
                    c["volumes"].append({
                        "name": parts[0],
                        "mountpoint": parts[1],
                    })
                # Translate environment parameters
                filename = container["env_file"][2:] if container["env_file"].startswith("./") else container["env_file"]
                p = envParser(config.servicepath + self.__name + "/" + filename)
                for var in p.getEnvironment():
                    c["environment"].append(var["name"])
                list.append(c)
        else:
            for container in self.__desc["containers"]:
                list.append(container["name"])
        return list

    # Returns the number of containers
    def getContainerCount(self):
        return len(self.getContainers())

    # Returns a container description for the given name
    def getContainerObject(self, name):
        for container in self.getContainers():
            if container["name"] == name:
                return container
        return False

    # Returns an array of all defined networks
    def getNetworks(self):
        if self.dockerComposeFile:
            networks = []
            for name, network in self.__desc["networks"].items():
                internal = True if "internal" in network else False
                networks.append({
                    "name": name,
                    "internal": internal,
                })
            return networks
        else:
            return self.__desc["networks"]

    # Returns an array of all defined volumes
    def getVolumes(self):
        if self.dockerComposeFile:
            volumes = []
            for name, volume in self.__desc["volumes"].items():
                volumes.append({
                    "name": name,
                })
            return volumes
        else:
            return self.__desc["volumes"]

    # Returns an array of all defined environment variables
    def getEnvironment(self):
        if self.dockerComposeFile:
            environment = []
            names = [] # Cache names we already have
            for name, container in self.__desc["services"].items():
                filename = container["env_file"][2:] if container["env_file"].startswith("./") else container["env_file"]
                p = envParser(config.servicepath + self.__name + "/" + filename)
                for var in p.getEnvironment():
                    if not var["name"] in names:
                        names.append(var["name"])
                        environment.append(var)
            return environment
        else:
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
