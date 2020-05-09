#!/usr/bin/env python3

# SchoolConnect Server-Manager - servermanager update background worker
# © 2019 Johannes Kreutz.

# Include dependencies
import os
from subprocess import Popen
from pathlib import Path
from time import sleep

# Helper function to empty and delete a folder
def emptyFolder(path, delete):
    for sub in path.iterdir():
        if sub.is_dir():
            emptyFolder(sub, True)
        else:
            sub.unlink()
    if delete:
        path.rmdir()

# Delete old files
sleep(5)
emptyFolder(Path("/usr/local/bin/servermanager/"), False)

# Move new files in place
copy = Popen(["cp", "-R", "/var/lib/servermanager/update/.", "/usr/local/bin/servermanager"])
copy.wait()

# Restart servermanager via systemd
restart = Popen(["sudo", "systemctl", "restart", "servermanager.service"])
restart.wait()
