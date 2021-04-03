#!/usr/bin/env python3

# SchoolConnect Server-Manager - service description class
# © 2019 - 2021 Johannes Kreutz.

# Include dependencies
import json
import urllib.request
import os
import yaml
from subprocess import Popen

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
            if os.path.exists(config.servicepath + self.__name + "/" + version + "/docker-compose.yml"):
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
            localPath = config.servicepath + self.__name + "/" + version + ".tar.gz"
        fs.filesystem.removeElement(localPath)
        urllib.request.urlretrieve(url, localPath)
        self.__version = version
        if self.dockerComposeFile:
            fs.filesystem.removeElement(config.servicepath + self.__name + "/" + version)
            os.makedirs(config.servicepath + self.__name + "/" + version)
            tar = Popen(["/bin/tar", "-zxf", config.servicepath + self.__name + "/" + version + ".tar.gz", "--directory", config.servicepath + self.__name + "/" + version, "--strip-components", "1"])
            tar.wait()
            fs.filesystem.removeElement(localPath)
        self.readDescriptionFile()

    # Reads a locally stored service file
    def readDescriptionFile(self):
        if self.dockerComposeFile:
            with open(config.servicepath + self.__name + "/" + self.__version + "/docker-compose.yml", "r") as serviceFile:
                self.__desc = yaml.safe_load(serviceFile.read())
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
            os.remove(config.servicepath + self.__name + "/" + self.__version)
        else:
            os.remove(config.servicepath + self.__name + "/service_" + version + ".json")

    # VALUE GETTERS
    # Returns a list of all containers
    def getContainers(self):
        list = []
        if self.dockerComposeFile:
            for name, container in self.__desc["services"].items():
                list.append(name)
        else:
            for container in self.__desc["containers"]:
                list.append(container["name"])
        return list

    # Returns the number of containers
    def getContainerCount(self):
        return len(self.getContainers())

    # Returns a container description for the given name
    def getContainerObject(self, name):
        for container in self.__getContainerObjectList():
            if container["name"] == name:
                return container
        return False

    # Returns an array of all defined networks
    def getNetworks(self):
        if self.dockerComposeFile:
            networks = []
            for name, network in self.__desc["networks"].items():
                internal = True if network is not None and "internal" in network else False
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
                if "env_file" in container:
                    for file in container["env_file"]:
                        filename = file[2:] if file.startswith("./") else file
                        p = envParser(config.servicepath + self.__name + "/" + self.__version + "/" + filename)
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
        elif "url" in container:
            response["url"] = container["url"]
        else:
            response["path"] = container["path"]
        return response

    # PRIVATE HELPERS
    # Get a list with all containet objects
    def __getContainerObjectList(self):
        if self.dockerComposeFile:
            list = []
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
                    c["path"] = config.servicepath + self.__name + "/" + self.__version + "/" + container["build"]
                # Translate ports
                if "ports" in container:
                    for port in container["ports"]:
                        parts = port.split(":")
                        c["ports"].append({
                            "external": parts[0],
                            "internal": parts[1],
                        })
                # Translate networks
                if "networks" in container:
                    for network in container["networks"]:
                        c["networks"].append({
                            "name": network,
                        })
                # Translate volumes
                if "volumes" in container:
                    for volume in container["volumes"]:
                        parts = volume.split(":")
                        c["volumes"].append({
                            "name": parts[0],
                            "mountpoint": parts[1],
                        })
                # Translate environment parameters
                if "env_file" in container:
                    for envFile in container["env_file"]:
                        filename = envFile[2:] if envFile.startswith("./") else envFile
                        p = envParser(config.servicepath + self.__name + "/" + self.__version + "/" + filename)
                        for var in p.getEnvironment():
                            c["environment"].append(var["name"])
                list.append(c)
            return list
        else:
            return self.__desc["containers"]
