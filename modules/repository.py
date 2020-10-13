#!/usr/bin/env python3

# SchoolConnect Server-Manager - service repository
# © 2019 Johannes Kreutz.

# Include dependencies
from pathlib import Path
import json
import requests
import time

# Class definition
class repository:
    def __init__(self):
        self.update()

    # Returns the module element with the given name if available
    def getModuleByName(self, wantedName):
        for name, module in self.__repo["modules"].items():
            if name == wantedName:
                return module
        return False

    # Checks if the actual version is older than 5 minutes and reloads it if necessary
    def updateIfRequired(self):
        if (time.time() - 300) > self.__lastupdate:
            self.update()

    # Reload repository
    def update(self):
        self.__lastupdate = time.time()
        self.__repo = json.loads(requests.get("https://philleconnect.org/assets/repository/repository.json").text)

    # Returns the url of the service with the given name for the specified version, if available
    def getUrl(self, name, wantedVersion):
        self.updateIfRequired()
        for version in self.getModuleByName(name)["versions"]:
            if version["version"] == wantedVersion:
                return version["url"]
        return False

    # Returns the latest available version number for the given service name, NOT respecting minimum required versions
    def getLatestAvailable(self, name):
        self.updateIfRequired()
        latest = None
        for version in self.getModuleByName(name)["versions"]:
            if "version" in version:
                if latest == None or self.compareVersions(latest["version"], version["version"]) == 1:
                    latest = version
        return latest

    # Returns all available versions for the given service name
    def getAllVersions(self, name):
        self.updateIfRequired()
        return self.getModuleByName(name)["versions"]

    # Returns a list of all available services for the given type
    def getAvailable(self, type):
        self.updateIfRequired()
        response = []
        for name, module in self.__repo["modules"].items():
            if module["type"] == type:
                moduleDescription = {
                    "name": name,
                    "description": module["description"],
                    "subscription": module["subscription"],
                }
                response.append(moduleDescription)
        return response

    # Returns the latest available version number for the given service name, respecting minimum required versions
    def getLatestCompatible(self, name, actual):
        self.updateIfRequired()
        if self.getLatestAvailable(name) == actual:
            return actual
        latestCompatible = None
        for version in self.getModuleByName(name)["versions"]:
            if self.compareVersions(version["required"], actual) >= 0 and latestCompatible == None or self.compareVersions(latestCompatible["version"], version["version"]) == 1:
                latestCompatible = version
        return latestCompatible["version"]

    # Returns if reverting to a previous version is possible with the actual installed version
    def isRevertPossible(self, name, actual):
        self.updateIfRequired()
        isPossible = False
        for version in self.getModuleByName(name)["versions"]:
            if "version" in version:
                if version["version"] == actual:
                    isPossible = version["revert"]
        return isPossible

    # Compares version numbers
    def compareVersions(self, v1, v2):
        l1 = v1.split(".")
        l2 = v2.split(".")
        for i in range(3):
            if int(l1[i]) > int(l2[i]):
                return -1
            elif int(l1[i]) < int(l2[i]):
                return 1
        return 0

    # Returns the type of this service
    def getType(self, name):
        return self.getModuleByName(name)["type"]
