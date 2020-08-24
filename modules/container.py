#!/usr/bin/env python3

# SchoolConnect Server-Manager - container class
# © 2019 Johannes Kreutz.

# Container status codes
# 0: Clean init
# 1: Finished and halted
# 2: Running
# 3: Building
# 4: Build failed
# 5: Not found (image or existing container)
# 6: Other error

# Include dependencies
import docker

# Include modules
import config
import modules.envstore as envstore

# Manager objects
env = envstore.envman()

# Create docker connection
client = docker.from_env()

# Class definition
class container:
    def __init__(self, exists, id):
        self.__status = 0
        if exists:
            try:
                self.__container = client.containers.get(container_id=id)
                self.__status = 1
            except docker.errors.NotFound:
                self.__status = 5
            except docker.errors.APIError:
                self.__status = 6
                print("Container lookup failed. Check inputs.")

    # Creates a new container and returns it
    def create(self, image, object, volumeSource = None):
        self.__status = 3
        extrahosts = {}
        if object["name"] == "pc_admin":
            extrahosts = {"docker.local":"192.168.255.255"}
        try:
            if self.__isHostNetwork(self.__firstNetwork(object)):
                if volumeSource == None:
                    self.__container = client.containers.create(image=image, auto_remove=False, detach=True, hostname=object["hostname"], ports=self.__createPortMap(object), restart_policy={"Name":"on-failure", "MaximumRetryCount": 5}, volumes=self.__createVolumeMap(object), name=object["name"], environment=self.__createEnvironmentMap(object), extra_hosts=extrahosts, network_mode="host")
                else:
                    self.__container = client.containers.create(image=image, auto_remove=False, detach=True, hostname=object["hostname"], ports=self.__createPortMap(object), restart_policy={"Name":"on-failure", "MaximumRetryCount": 5}, volumes_from=volumeSource, name=object["name"], environment=self.__createEnvironmentMap(object), extra_hosts=extrahosts, network_mode="host")
            else:
                if volumeSource == None:
                    self.__container = client.containers.create(image=image, auto_remove=False, detach=True, hostname=object["hostname"], ports=self.__createPortMap(object), restart_policy={"Name":"on-failure", "MaximumRetryCount": 5}, volumes=self.__createVolumeMap(object), name=object["name"], environment=self.__createEnvironmentMap(object), extra_hosts=extrahosts, network=self.__firstNetwork(object)["name"])
                else:
                    self.__container = client.containers.create(image=image, auto_remove=False, detach=True, hostname=object["hostname"], ports=self.__createPortMap(object), restart_policy={"Name":"on-failure", "MaximumRetryCount": 5}, volumes_from=volumeSource, name=object["name"], environment=self.__createEnvironmentMap(object), extra_hosts=extrahosts, network=self.__firstNetwork(object)["name"])
            self.__status = 1
            return 0
        except docker.errors.ContainerError:
            self.__status = 4
            return 1
        except docker.errors.ImageNotFound:
            self.__status = 5
            return 2
        except docker.errors.APIError:
            self.__status = 6
            print("Container build failed. Check inputs.")
            return 3

    # Renames this container
    def rename(self, newName):
        self.__container.rename(name=newName)
        self.__container.reload()

    # Returns this containers id
    def getId(self):
        return self.__container.id

    # Returns this containers actual name
    def getName(self):
        return self.__container.name

    # Starts this container
    def start(self):
        self.__container.start()
        self.__status = 2

    # Stops this container
    def stop(self):
        if hasattr(self, "__container"):
            self.__container.stop()
            self.__status = 1

    # Returns if this container is actually running
    def isRunning(self):
        if self.__container.status == "running":
            return True
        else:
            return False

    # Deletes this container
    def delete(self):
        if hasattr(self, "__container"):
            try:
                self.__container.remove(v=False)
            except docker.errors.NotFound:
                pass

    # Returns the container status
    def getStatus(self):
        switcher = {
            0: "undefined",
            1: "paused",
            2: "running",
            3: "building",
            4: "builderror",
            5: "inaccessible",
            6: "error"
        }
        return switcher.get(self.__status, False)

    # PRIVATE HELPER FUNCTIONS
    # Creates a port map for the docker api
    def __createPortMap(self, object):
        portMap = {}
        if "ports" in object:
            for port in object["ports"]:
                portMap[port["internal"]] = port["external"]
        return portMap

    # Creates an environment variable map for the docker api
    def __createEnvironmentMap(self, object):
        environmentMap = {}
        if "environment" in object:
            for var in object["environment"]:
                environmentMap[var] = env.getValue(var)
        if object["name"] == "pc_admin":
            apitokenfile = open(config.configpath + config.apitokenfile, "r")
            environmentMap["APIKEY"] = apitokenfile.read()
            apitokenfile.close()
        return environmentMap

    # Creates a volume map for the docker api
    def __createVolumeMap(self, object):
        volumeMap = {}
        if "volumes" in object:
            for wantedVolume in object["volumes"]:
                volumeMap[wantedVolume["name"]] = {"bind": wantedVolume["mountpoint"], "mode": "rw"}
        if "userdata" in object:
            volumeMap[env.getValue("USERDATA")] = {"bind": object["userdata"], "mode": "rw"}
        return volumeMap

    # Returns the first network
    def __firstNetwork(self, object):
        return object["networks"][0] if len(object["networks"]) > 0 else None

    # Returns if the given network description object describes a host network
    def __isHostNetwork(self, networkObject):
        return True if "host" in networkObject else False
