#!/usr/bin/env python3

# SchoolConnect Server-Manager - docker delete script
# © 2019 Johannes Kreutz.

# Include dependencies
import docker
import sys
import os
import json

# Include modules
import config

# Create docker connection
client = docker.from_env()

# Loop through services
if len(sys.argv) > 1 and sys.argv[1] == "yes":
    for filename in os.listdir(config.servicepath):
        if os.path.isdir(config.servicepath + filename) and "buildcache" not in filename:
            conffile = open(config.servicepath + filename + "/config.json", "r")
            configobj = json.loads(conffile.read())
            for container in configobj["containers"]["actual"]:
                ct = client.containers.get(container_id=container["id"])
                ct.stop()
                ct.remove(v=True, force=True)
            for container in configobj["containers"]["previous"]:
                ct = client.containers.get(container_id=container["id"])
                ct.stop()
                ct.remove(v=True, force=True)
            client.images.prune()
            client.networks.prune()
            client.volumes.prune()
else:
    print("Please confirm your decision by running 'dockerdelete.py yes'")
