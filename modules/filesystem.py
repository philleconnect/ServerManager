#!/usr/bin/env python3

# SchoolConnect Server-Manager - filesystem helpers
# © 2019 Johannes Kreutz.

# Include dependencies
import os
from pathlib import Path

# Class definition
class filesystem:
    # Removes given element, wether it's a file or folder
    @staticmethod
    def removeElement(path):
        if os.path.exists(path):
            if os.path.isdir(path):
                filesystem.emptyFolderWorker(Path(path))
            else:
                os.remove(path)

    # Deletes everythin inside the given folder
    @staticmethod
    def emptyFolder(path):
        filesystem.emptyFolderWorker(Path(path))

    # Helper
    @staticmethod
    def emptyFolderWorker(path):
        for sub in path.iterdir():
            if sub.is_dir():
                filesystem.emptyFolderWorker(sub)
            else:
                sub.unlink()
        path.rmdir()
