#!/usr/bin/env python3

# SchoolConnect Server-Manager - service class
# © 2019 - 2021 Johannes Kreutz.

# Possible service wantings
# running: Service is up and running
# paused: Service is installed, but not running

# Possible service stats
# running: Service is up and running
# paused: Service is installed, but not running
# installing: Service is being installed
# installPending: Service is waiting for user input (environment variables)
# preparing: Service is preparing installation (checking environment variables, creating volumes and networks etc.)
# installed: Service installation is finished
# empty: Service is freshly created but not initialized yet
# updating: Service is being updated
# updatePending: Service is waiting for user input (environment variables)
# reverting: Service is reverting to previous version
# deleting: Service is being deleted
# deleted: Service is removed
# undefined: Something went wrong and the service is in an undefined state

# Include dependencies
import os
import json
import threading
import time
import queue
from subprocess import Popen

# Include modules
import config
import modules.container as container
import modules.volume as volume
import modules.network as network
import modules.prune as prune
import modules.servicedescription as description
import modules.filesystem as fs
import modules.builderThread as bt
import modules.repository as repository
from modules.envstore import envman

# Manager objects
env = envman()

# Class definition
class service:
    networks = []
    def __init__(self, name, firstinstall):
        # Init vars
        self.__name = name
        self.__containers = {"actual":[],"previous":[]}
        self.__volumes = []
        self.__description = None
        self.__errors = 0
        self.__installThread = None
        self.__updateThread = None
        self.__revertThread = None
        self.__deleteThread = None
        self.__rebuildThread = None
        self.__localEnv = None
        if not firstinstall:
            # Read container configuration
            configFile = open(config.servicepath + name + "/config.json", "r")
            self.__config = json.loads(configFile.read())
            configFile.close()
            # Create service description object
            self.__desc = description.serviceDescription(False, self.__name, self.__config["actualVersion"])
            self.__localEnv = envman(self.__name)
            # Create docker references for volumes
            for storedVolume in self.__config["volumes"]:
                self.__volumes.append(volume.volume(True, storedVolume["id"], None))
            # Create docker references for networks
            for storedNetwork in self.__config["networks"]:
                self.networks.append(network.network(True, storedNetwork["id"], None, None))
            # Create docker references for containers
            for storedContainer in self.__config["containers"]["actual"]:
                self.__containers["actual"].append(container.container(True, storedContainer["id"], self.__name))
            for storedContainer in self.__config["containers"]["previous"]:
                self.__containers["previous"].append(container.container(True, storedContainer["id"], self.__name))
            # Check container status and turn containers to wanted status
            if self.__config["wanted"]:
                for containerObject in self.__containers["actual"]:
                    if not containerObject.isRunning():
                        containerObject.start()
                self.__config["status"] = "running"
            else:
                for containerObject in self.__containers["actual"]:
                    if containerObject.isRunning():
                        containerObject.stop()
                self.__config["status"] = "paused"
        else:
            self.__config = {
                "networks": [],
                "volumes": [],
                "containers": {"actual":[],"previous":[]},
                "wanted": True,
                "status": "empty",
                "actualVersion": "",
                "previousVersion": "",
            }

    # SERVICE BUILDING
    # Build a version of this service
    def prepareBuild(self, name, url, version):
        if self.__config["status"] != "empty":
            print("Error calling prepareBuild: this service is not in 'empty' state")
            return False
        self.__name = name
        self.__config["status"] = "preparing"
        self.__config["actualVersion"] = version
        # Create service folder
        fs.filesystem.removeElement(config.servicepath + name)
        os.makedirs(config.servicepath + name)
        self.__saveConfiguration()
        # Download service description
        self.__desc = description.serviceDescription(True, self.__name, self.__config["actualVersion"], url)
        self.__localEnv = envman(self.__name)
        # Check if all required environment variables are set
        requiredVars = self.__requiredEnvironmentVariables()
        self.__config["status"] = "installPending"
        if requiredVars == False:
            return True
        else:
            self.__saveConfiguration()
            return requiredVars

    # Return a dict with all required environment variables, or false if there are none
    def __requiredEnvironmentVariables(self):
        requiredVars = {}
        for var in self.__desc.getEnvironment():
            if "private" in var and var["private"] == True:
                if not self.__localEnv.doesKeyExist(var["name"]):
                    if "default" in var:
                        self.__localEnv.storeValue(var["name"], var["default"], var["description"], var["mutable"])
                    else:
                        requiredVars["[" + self.__name + "]" + var["name"]] = {"description":var["description"],"mutable":var["mutable"]}
            else:
                if not env.doesKeyExist(var["name"]):
                    if "default" in var:
                        env.storeValue(var["name"], var["default"], var["description"], var["mutable"])
                    else:
                        requiredVars[var["name"]] = {"description":var["description"],"mutable":var["mutable"]}
        if len(requiredVars) > 0:
            return requiredVars
        else:
            return False

    # Thread wrapper for continue installation
    def asyncContinueInstallation(self):
        self.__installThread = threading.Thread(target = self.continueInstallation)
        self.__installThread.start()

    # Continues installation if all requirements are fulfilled
    def continueInstallation(self):
        self.__config["status"] = "installing"
        requiredVars = self.__requiredEnvironmentVariables()
        if requiredVars != False:
            return False
        self.__buildInfrastructure()
        self.__saveConfiguration()
        containerList = self.__desc.getContainers()
        # Prepare threads
        self.__buildThreads = []
        self.__queueLock = threading.Lock()
        self.__buildQueue = queue.Queue(self.__desc.getContainerCount())
        self.__containerArray = []
        # Add containers to queue
        self.__queueLock.acquire()
        for name in containerList:
            containerObject = {"object":self.__desc.getContainerObject(name),"image":self.__desc.getImageSource(name),"volumeSource":None,"name":self.__name}
            self.__buildQueue.put(containerObject)
        self.__queueLock.release()
        # Create and start threads
        for x in range(self.__desc.getContainerCount()):
            thread = bt.builderThread(x, self.__buildQueue, self.__queueLock, self.__containerArray)
            thread.start()
            self.__buildThreads.append(thread)
        # Wait for the threads to end
        for thread in self.__buildThreads:
            thread.join()
        # Store all containers
        for container in self.__containerArray:
            self.__config["containers"]["actual"].append({"name":container["container"].getName(), "id":container["container"].getId(), "image":container["image"]})
            self.__containers["actual"].append(container["container"])
            self.__saveConfiguration()
            self.__connectNetworks(container["container"].getName())
        self.__config["status"] = "paused"

    # Build infrastructure around the containers (volumes and networks)
    def __buildInfrastructure(self):
        # Create volumes
        for newVolume in self.__desc.getVolumes():
            if self.__getVolumeByName(newVolume["name"]) == False:
                createdVolume = self.__createNewVolume(newVolume["name"])
                self.__config["volumes"].append({"id":createdVolume.getId()})
                self.__volumes.append(createdVolume)
        # Create networks
        for newNetwork in self.__desc.getNetworks():
            if self.__getNetworkByName(newNetwork["name"]) == False:
                createdNetwork = self.__createNewNetwork(newNetwork["name"], newNetwork["internal"])
                self.__config["networks"].append({"id":createdNetwork.getId()})
                self.networks.append(createdNetwork)

    # Create a new docker network
    def __createNewNetwork(self, name, internal):
        return network.network(False, None, name, internal)

    # Create a new docker volume
    def __createNewVolume(self, name):
        return volume.volume(False, None, name)

    # Connects the other networks to a created container
    def __connectNetworks(self, name):
        object = self.__desc.getContainerObject(name)
        if len(object["networks"]) > 1:
            first = True
            for nwdesc in object["networks"]:
                if not first:
                    self.__getNetworkByName(nwdesc["name"]).connect(self.__getContainerByName(name).getId(), [object["hostname"]])
                else:
                    first = False

    # SERVICE CONTROLLING
    # Start all containers of this service in the order defined in the service description
    def start(self):
        self.__config["wanted"] = True
        self.__saveConfiguration()
        for name in self.__desc.getContainers():
            self.__getContainerByName(name).start()
        self.__config["status"] = "running"
        self.__saveConfiguration()

    # Stop all containers of this service
    def stop(self):
        self.__config["wanted"] = False
        self.__saveConfiguration()
        for containerObject in self.__containers["actual"]:
            containerObject.stop()
        self.__config["status"] = "paused"
        self.__saveConfiguration()

    # SERVICE INFORMATIONS
    # Return name
    def getName(self):
        return self.__name

    # Return actual service status
    def getStatus(self):
        return self.__config["status"]

    # Return the installed version of this service
    def getInstalledVersion(self):
        return self.__config["actualVersion"]

    # Return if the service is running
    def isRunning(self):
        for ct in self.__containers["actual"]:
            if not ct.isRunning():
                return False
        return True

    # Return if the service should be running
    def shouldRun(self):
        return self.__config["wanted"]

    # Return if the service is in it's wanted state
    def isOk(self):
        return self.shouldRun() == self.isRunning()

    # Return if a pervious version is available
    def hasPrevious(self):
        return self.__config["previousVersion"]

    # SERVICE DELETION
    # Thread wrapper for delete
    def asyncDelete(self):
        repo = repository.repository()
        if repo.getType(self.__name) == "essential":
            return "ERR_IS_ESSENTIAL"
        else:
            self.__deleteThread = threading.Thread(target = self.__delete)
            self.__deleteThread.start()
            return "running"

    # Delete service
    def __delete(self):
        self.__config["status"] = "deleting"
        self.stop()
        self.__config["status"] = "deleting"
        self.__saveConfiguration()
        for container in self.__containers["actual"]:
            container.delete()
        for container in self.__containers["previous"]:
            container.delete()
        for volume in self.__volumes:
            volume.delete()
        prune.prune.networks()
        prune.prune.images()
        fs.filesystem.removeElement(config.servicepath + self.__name)
        self.__config["status"] = "deleted"

    # SERVICE UPDATE
    # Update preparation
    def prepareUpdate(self, url, version):
        # First remove any trash of the previous version
        for ct in self.__containers["previous"]:
            ct.stop()
            ct.delete()
        fs.filesystem.removeElement(config.servicepath + self.__name + "/service_" + self.__config["previousVersion"] + ".json")
        # Move actual to previous version
        self.__config["previousVersion"] = self.__config["actualVersion"]
        self.__config["actualVersion"] = version
        self.__config["status"] = "updatePending"
        self.__saveConfiguration()
        # Download new service description
        self.__desc = description.serviceDescription(True, self.__name, self.__config["actualVersion"], url)
        # Check for new environment variables
        vars = self.__requiredEnvironmentVariables()
        if vars != False:
            return vars
        else:
            return "running"

    # Threaded wrapper for update
    def asyncUpdate(self):
        self.__config["status"] = "updating"
        self.__saveConfiguration()
        self.__updateThread = threading.Thread(target = self.__update)
        self.__updateThread.start()

    # Run update
    def __update(self):
        requiredVars = self.__requiredEnvironmentVariables()
        if requiredVars != False:
            return False
        # Stop all running containers
        self.stop()
        # Backup all volume contents
        for volume in self.__volumes:
            backupPath = env.getValue("USERDATA") + "/PreviousVersions/" + volume.getName() + "_" + self.__config["previousVersion"]
            if os.path.exists(backupPath):
                remover = Popen(["sudo", "/usr/local/bin/servermanager/volumebackup.py", backupPath, "delete"])
                remover.wait()
            os.makedirs(backupPath)
            volume.backupContent(backupPath)
        # Rename the existing containers and move them to previous
        self.__config["containers"]["previous"].clear()
        for ct in self.__config["containers"]["actual"]:
            self.__config["containers"]["previous"].append(ct)
        self.__config["containers"]["actual"].clear()
        for ct in self.__containers["actual"]:
            self.__containers["previous"].append(ct)
            ct.rename(ct.getName() + "_" + self.__config["previousVersion"])
        self.__containers["actual"].clear()
        # Build the new containers
        self.continueInstallation()
        self.__config["status"] = "updating"
        # Start the new containers
        self.start()
        self.__config["status"] = "running"
        self.__saveConfiguration()

    # SERVICE REVERT TO PREVIOUS
    # Threaded wrapper for revert
    def asyncRevert(self):
        self.__config["status"] = "reverting"
        self.__saveConfiguration()
        self.__revertThread = threading.Thread(target=self.revert)
        self.__revertThread.start()
        return "running"

    # Revert to the previous version of this service, if available
    def revert(self):
        # Stop the actual containers
        self.stop()
        # Delete the actual containers and store their names
        names = []
        for ct in self.__containers["actual"]:
            names.append(ct.getName())
            ct.delete()
        # Move the old containers back to actual
        self.__containers["actual"].clear()
        for ct in self.__containers["previous"]:
            self.__containers["actual"].append(ct)
        self.__containers["previous"].clear()
        self.__config["containers"]["actual"].clear()
        for ct in self.__config["containers"]["previous"]:
            self.__config["containers"]["actual"].append(ct)
        self.__config["containers"]["previous"].clear()
        # Rename old containers back to original name
        for ct in self.__containers["actual"]:
            for name in names:
                if name + "_" + self.__config["previousVersion"] == ct.getName():
                    ct.rename(name)
        # Read old service description
        self.__desc = description.serviceDescription(False, self.__name, self.__config["previousVersion"])
        # Restore volumes
        for volume in self.__volumes:
            backupPath = env.getValue("USERDATA") + "/PreviousVersions/" + volume.getName() + "_" + self.__config["previousVersion"]
            volume.restoreContent(backupPath)
            delete = Popen(["sudo", "/usr/local/bin/servermanager/volumebackup.py", backupPath, "delete"])
            delete.wait()
        # Start old containers
        self.start()
        self.__config["status"] = "running"
        self.__saveConfiguration()
        # Delete files
        fs.filesystem.removeElement(config.servicepath + self.__name + "/service_" + self.__config["actualVersion"] + ".json")
        # Revert version number
        self.__config["actualVersion"] = self.__config["previousVersion"]
        self.__config["previousVersion"] = ""
        self.__saveConfiguration()

    # SERVICE REBUILD
    # Prepare rebuilding thread
    def prepareRebuild(self):
        self.__config["status"] = "installing"
        self.__saveConfiguration()
        self.__rebuildThread = threading.Thread(target=self.rebuild)
        self.__rebuildThread.start()
        return "running"

    # Execute container rebuild
    def rebuild(self):
        # Stop the actual containers
        self.stop()
        # Remove the actual containers
        for ct in self.__containers["actual"]:
            ct.delete()
        # Clear the arrays
        self.__containers["actual"].clear()
        self.__config["containers"]["actual"].clear()
        # Build the new containers
        self.continueInstallation()
        # Start the new containers
        self.start()
        self.__config["status"] = "running"
        self.__saveConfiguration()

    # PRIVATE HELPER FUNCTIONS
    # Returns the network object by its name
    def __getNetworkByName(self, name):
        if name == "schoolconnect":
            mainconfig = open(config.servicepath + "config.json", "r")
            globalNetwork = network.network(True, json.loads(mainconfig.read())["globalNetwork"], None, False)
            mainconfig.close()
            return globalNetwork
        for nw in self.networks:
            if nw.getName() == name:
                return nw
        return False

    # Returns the container object by its name
    def __getContainerByName(self, name):
        for container in self.__containers["actual"]:
            if container.getName() == name:
                return container
        for container in self.__containers["previous"]:
            if container.getName() == name:
                return container
        return None

    # Returns the volume object by its id
    def __getVolumeById(self, id):
        for vol in self.__volumes:
            if vol.getId() == id:
                return vol
        return False

    # Returns the volume object by its name
    def __getVolumeByName(self, name):
        for vol in self.__volumes:
            if vol.getName() == name:
                return vol
        return False

    # Save service configuration to config.json
    def __saveConfiguration(self):
        configFile = open(config.servicepath + self.__name + "/config.json", "w")
        configFile.write(json.dumps(self.__config, sort_keys=True, indent=4))
        configFile.close()
