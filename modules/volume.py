#!/usr/bin/env python3

# SchoolConnect Server-Manager - volume class
# © 2019 Johannes Kreutz.

# Include dependencies
import docker
from subprocess import Popen

# Include modules
import config
import modules.filesystem as fs

# Create docker connection
client = docker.from_env()

# Class definition
class volume:
    def __init__(self, exists, id, name):
        if exists:
            try:
                self.__volume = client.volumes.get(volume_id=id)
            except docker.errors.NotFound:
                print("Volume not found. Check inputs.")
            except docker.errors.APIError:
                print("Volume lookup failed. Check inputs.")
        else:
            try:
                self.__volume = client.volumes.create(name=name, driver="local")
            except docker.errors.APIError:
                print("Volume creation failed. Check inputs.")

    # Returns the name of this volume
    def getName(self):
        return self.__volume.name

    # Returns the id of this volume
    def getId(self):
        return self.__volume.id

    # Backups the data content to the given folder. EVERYTING IN THE DESTINATION PATH WILL BE DELETED! WARNING: RUNNING THIS ON A RUNING CONTAINER MIGHT RESULT IN CORRUPTED BACKUPS!
    def backupContent(self, destPath):
        backup = Popen(["sudo", "/usr/local/bin/servermanager/volumebackup.py", destPath, self.__volume.name])
        backup.wait()

    # DANGEROUS: Restore a data content backup. RUN THIS ONLY WHEN THE CONTAINER IS PAUSED! RESTORING INTO A RUNNING CONTAINER MIGHT RESULT IN CORRUPTED DATA AND BROKEN SERVICES!
    def restoreContent(self, sourcePath):
        restore = Popen(["sudo", "/usr/local/bin/servermanager/volumebackup.py", sourcePath, self.__volume.name, "restore"])
        restore.wait()

    # DANGEROUS: Deletes this volume and its data
    def delete(self):
        self.__volume.remove()
