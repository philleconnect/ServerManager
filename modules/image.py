#!/usr/bin/env python3

# SchoolConnect Server-Manager - image class
# © 2019 Johannes Kreutz.

# Image status definitions
# 0: Clean init
# 1: Successfully built
# 2: Building
# 3: Not found
# 4: Building failed
# 5: Other APIError

# Include dependencies
import docker
import urllib.request
import os
from subprocess import Popen

# Include modules
import config
import modules.filesystem as fs
import modules.essentials as ess

# Create docker connection
client = docker.from_env()

# Class definition
class image:
    def __init__(self, exists, name):
        self.__status = 0
        self.__name = name
        if exists:
            try:
                self.__image = client.images.get(name=name)
                self.__status = 1
            except docker.errors.ImageNotFound:
                self.__status = 3
                print("Image not found. Check inputs.")
            except docker.errors.APIError:
                self.__status = 5
                print("Image lookup failed. Check inputs.")

    # Creates a new image based on a container description object and a version string. Returns id of the new image
    def create(self, object, wantedVersion):
        if self.__status != 0:
            return False
        self.__status = 2
        self.__name = object["name"]
        self.__wantedVersion = wantedVersion
        if "prebuilt" in self.__wantedVersion:
            return self.__pull(self.__wantedVersion["prebuilt"]["name"] + ":" + self.__wantedVersion["prebuilt"]["version"])
        else:
            return self.__build(self.__wantedVersion["url"])

    # Pulls an image from the docker hub
    def __pull(self, name):
        try:
            self.__image = client.images.pull(name)
            self.__status = 1
            return self.__image.id
        except docker.errors.APIError:
            self.__status = 5
            return False

    # Builds an image from a given url
    def __build(self, url):
        if not os.path.exists(config.servicepath + "buildcache"):
            os.makedirs(config.servicepath + "buildcache")
        randomString = ess.essentials.randomString(10)
        fs.filesystem.removeElement(config.servicepath + "buildcache/" + self.__name + "_" + randomString)
        fs.filesystem.removeElement(config.servicepath + "buildcache/" + self.__name + "_" + randomString + ".tar.gz")
        os.makedirs(config.servicepath + "buildcache/" + self.__name + "_" + randomString)
        urllib.request.urlretrieve(url, config.servicepath + "buildcache/" + self.__name + "_" + randomString + ".tar.gz")
        tar = Popen(["/bin/tar", "-zxf", config.servicepath + "buildcache/" + self.__name + "_" + randomString + ".tar.gz", "--directory", config.servicepath + "buildcache/" + self.__name + "_" + randomString])
        tar.wait()
        fs.filesystem.removeElement(config.servicepath + "buildcache/" + self.__name + "_" + randomString + ".tar.gz")
        dircount = 0
        dirname = ""
        for filename in os.listdir(config.servicepath + "buildcache/" + self.__name + "_" + randomString):
            if os.path.isdir(config.servicepath + "buildcache/" + self.__name + "_" + randomString + "/" + filename):
                dirname = filename
                dircount += 1
        if dircount != 1:
            return False
        try:
            self.__image = client.images.build(path=config.servicepath + "buildcache/" + self.__name + "_" + randomString + "/" + dirname, rm=True)[0]
            fs.filesystem.removeElement(config.servicepath + "buildcache/" + self.__name + "_" + randomString)
            self.__status = 1
            return self.__image.id
        except docker.errors.BuildError:
            self.__status = 4
            return False
        except docker.errors.APIError:
            self.__status = 5
            print("Image building failed. Check inputs.")
            return False

    # Returns the id of this image
    def getId(self):
        if self.__image != None:
            return self.__image.id
        return False

    # Deletes this image from the local machine
    def delete(self):
        client.images.remove(image=self.__name)
