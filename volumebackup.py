#!/usr/bin/env python3

# SchoolConnect Server-Manager - container volume data copy script
# © 2019 - 2020 Johannes Kreutz.

# Include dependencies
import shutil
import os
from pathlib import Path
import sys

# Include modules
import modules.filesystem as fs

# Main logic
if len(sys.argv) == 3:
    if sys.argv[2] == "delete":
        if not "/var/lib/docker/volumes/" in sys.argv[1]:
            fs.filesystem.removeElement(sys.argv[1])
    else:
        if not os.path.exists(sys.argv[1]) and not os.path.isdir(sys.argv[1]):
            sys.exit()
        fs.filesystem.emptyFolder(sys.argv[1])
        shutil.copytree("/var/lib/docker/volumes/" + sys.argv[2], sys.argv[1] + "/", symlinks=True, ignore=None)
elif len(sys.argv) == 4:
    if sys.argv[3] == "restore":
        fs.filesystem.emptyFolder("/var/lib/docker/volumes/" + sys.argv[2])
        shutil.copytree(sys.argv[1], "/var/lib/docker/volumes/" + sys.argv[2] + "/", symlinks=True, ignore=None)
else:
    print("ERROR: Wrong number of parameters.")
