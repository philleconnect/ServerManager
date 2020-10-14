#!/usr/bin/env python3

# SchoolConnect Server-Manager - servermanager update
# © 2019 - 2020 Johannes Kreutz.

# Include dependencies
import urllib.request
import os
from subprocess import Popen
from pathlib import Path

# Include modules
import config
import modules.repository as repository

# Manager objects
repo = repository.repository()

# Class definition
class managerupdate:
    # Wrapper to install a new servermanager version
    @staticmethod
    def installUpdate(version):
        managerupdate.backup()
        managerupdate.downloadVersion(repo.getUrl("servermanager", version), version)
        managerupdate.doUpdateInstallation()

    # Helper function to empty and delete a folder
    @staticmethod
    def emptyFolder(path):
        for sub in path.iterdir():
            if sub.is_dir():
                managerupdate.emptyFolder(sub)
            else:
                sub.unlink()
        path.rmdir()

    # Backup old version
    @staticmethod
    def backup():
        # Delete old backups
        if os.path.exists(config.backuppath + "backup"):
            managerupdate.emptyFolder(Path(config.backuppath + "backup"))
        # Create a new backup folder
        os.makedirs(config.backuppath + "backup", 0o777)
        # Copy actual servermanager executable files
        copyresult = Popen(["cp", "-R", config.managerpath + ".", config.backuppath + "backup"])
        copyresult.wait()

    # Download and extract a new servermanager version
    @staticmethod
    def downloadVersion(url, version):
        # Cleanup first
        if os.path.exists(config.backuppath + "update"):
            managerupdate.emptyFolder(Path(config.backuppath + "update"))
        # Download and extract
        os.makedirs(config.backuppath + "update", 0o777)
        urllib.request.urlretrieve(url, config.backuppath + "servermanager_update.tar.gz")
        tar = Popen(["/bin/tar", "-zxf", config.backuppath + "servermanager_update.tar.gz", "--directory", config.backuppath])
        tar.wait()
        os.remove(config.backuppath + "servermanager_update.tar.gz")
        copy = Popen(["cp", "-R", config.backuppath + "servermanager/.", config.backuppath + "update"])
        copy.wait()
        managerupdate.emptyFolder(Path(config.backuppath + "servermanager"))

    # Install a downloaded version
    @staticmethod
    def doUpdateInstallation():
        Popen(["nohup", "python3", config.backuppath + "update/update.py"])
