#!/usr/bin/env python3

# SchoolConnect Server-Manager
# © 2019 Johannes Kreutz.

# Include dependencies
import sys
import os
import json
from flask import Flask, request

# Include modules
import config
import modules.repository as repository
import modules.service as service
import modules.network as network
import modules.envstore as envstore
import modules.managerupdate as update
import modules.essentials as ess

# Manager objects
repo = repository.repository()
env = envstore.envman()
api = Flask(__name__)

# Variables
services = []
globalNetwork = None

# First setup
if len(sys.argv) > 1 and sys.argv[1] == "firstsetup":
    if os.path.exists(config.configpath + ".ServerManagerSetupDone"):
        print("SchoolConnect Server-Manager seems to be installed already. If you think this is an error, delete the file '.SchoolConnectSetupDone' and run this again.")
        sys.exit()
    # Store fixed environment variables
    env.storeValue("MYSQL_DATABASE", "schoolconnect", "Name der Hauptdatenbank.", False)
    env.storeValue("MYSQL_USER", "pc_admin_mysql_user", "Nutzername für die Hauptdatenbank.", False)
    env.storeValue("MYSQL_PASSWORD", ess.essentials.randomString(128), "Interne Zugangskennung für die Hauptdatenbank.", False)
    #env.storeValue("POSTGRES_DB", "hydra", "Name der Authentifizierungsdatenbank.", False)
    #env.storeValue("POSTGRES_USER", "hydra_user", "Nutzername für die Authentifizierungsdatenbank.", False)
    #env.storeValue("POSTGRES_PASSWORD", ess.essentials.randomString(128), "Interne Zugangskennung für die Authentifizierungsdatenbank.", False)
    #env.storeValue("SECRETS_SYSTEM", ess.essentials.randomString(128), "Sicherheitsschlüssel für Ory Hydra.", False)
    #env.storeValue("OIDC_SUBJECT_TYPE_PAIRWISE_SALT", ess.essentials.randomString(128), "OpenID Connect Sicherheits-Salt 'pairwise'.", False)
    env.storeValue("MANAGEMENT_APIS_SHARED_SECRET", ess.essentials.randomString(256), "Shared Secret für Management-APIs.", False)
    # Create main network
    globalNetwork = network.network(False, None, "schoolconnect", False)
    mainconfig = open(config.servicepath + "config.json", "w")
    mainconfig.write(json.dumps({"globalNetwork":globalNetwork.getId()}))
    mainconfig.close()
    # Create api token for pc_admin
    apitokenfile = open(config.configpath + config.apitokenfile, "w")
    apitokenfile.write(ess.essentials.randomString(512))
    apitokenfile.close()
    # Create essential services and containers
    essentials = repo.getAvailable("essential")
    for essential in essentials:
        latestVersion = repo.getLatestAvailable(essential["name"])
        newService = service.service(essential["name"], True)
        newService.prepareBuild(essential["name"], latestVersion["url"], latestVersion["version"])
        newService.continueInstallation()
        services.append(newService)
    sys.exit()


# Normal startup
# Get main network reference
mainconfig = open(config.servicepath + "config.json", "r")
globalNetwork = network.network(True, json.loads(mainconfig.read())["globalNetwork"], None, False)
mainconfig.close()
# Check for installed services - create objects
for filename in os.listdir(config.servicepath):
    if os.path.isdir(config.servicepath + filename) and "buildcache" not in filename:
        newService = service.service(filename, False)
        services.append(newService)

# Helper functions
# Return the service with the given Name
def getServiceByName(name):
    for service in services:
        if service.getName() == name:
            return service
    return False
# Returns if a service is installed
def isInstalled(name):
    for service in services:
        if service.getName() == name:
            return True
    return False
# Returns api key
def getApiKey():
    apitokenfile = open(config.configpath + config.apitokenfile, "r")
    token = apitokenfile.read()
    apitokenfile.close()
    return token

# Servermanager update
def installManagerUpdate(version):
    return True

# API REQUESTS
# Server testing
@api.route("/", methods=["POST"])
def index():
    return "Hey there! I'm up and running!"

# STATUS CHECKS
# Get available containers and their status
@api.route("/status", methods=["POST"])
def getServices():
    data = request.form
    if data.get("apikey") == getApiKey():
        status = []
        for service in services:
            previous = service.hasPrevious()
            if previous != "":
                if not repo.isRevertPossible(service.getName(), service.getInstalledVersion()):
                    previous = ""
            status.append({
                "name": service.getName(),
                "version": service.getInstalledVersion(),
                "wanted": service.shouldRun(),
                "status": service.getStatus(),
                "running": service.isRunning(),
                "previous": previous,
                "type": repo.getType(service.getName())
            })
        return json.dumps(status)
    else:
        return json.dumps({"error":"ERR_AUTH"})

# DATA LOADING
# Get all available containers
@api.route("/repo", methods=["POST"])
def getAvailable():
    data = request.form
    if data.get("apikey") == getApiKey():
        availableServices = repo.getAvailable("plugin")
        installableServices = []
        for availableService in availableServices:
            availableService["installed"] = isInstalled(availableService["name"])
            installableServices.append(availableService)
        return json.dumps(installableServices)
    else:
        return json.dumps({"error":"ERR_AUTH"})

# SERVICE CONTROL
# Start or stop a service
@api.route("/control", methods=["POST"])
def controlService():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service == False:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
        else:
            if data.get("action") == "start":
                service.start()
            else:
                service.stop()
            return json.dumps({"result":service.getStatus()})
    else:
        return json.dumps({"error":"ERR_AUTH"})

# SERVICE INSTALLATION
# Install new service
@api.route("/install", methods=["POST"])
def installService():
    data = request.form
    if data.get("apikey") == getApiKey():
        latestVersion = repo.getLatestAvailable(data.get("service"))
        if latestVersion != None:
            newService = service.service(None, True)
            services.append(newService)
            return json.dumps({"result":newService.prepareBuild(data.get("service"), latestVersion["url"], latestVersion["version"])})
        else:
            return json.dumps({"error":"ERR_SERVICE_NOT_AVAILABLE"})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Delete service
@api.route("/delete", methods=["POST"])
def deleteService():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service != False:
            return json.dumps({"result":service.asyncDelete()})
        else:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
    else:
        return json.dumps({"error":"ERR_AUTH"})

# SERVICE UPDATING
# Execute a service update
@api.route("/executeupdate", methods=["POST"])
def executeUpdate():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service != False:
            return json.dumps({"result":service.prepareUpdate(repo.getUrl(data.get("service"), data.get("version")), data.get("version"))})
        else:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Check the status of a running update
@api.route("/actionstatus", methods=["POST"])
def checkActionStatus():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service != False:
            status = service.getStatus()
            if status == "updatePending":
                service.asyncUpdate()
                return json.dumps({"result":"updating"})
            elif status == "installPending":
                service.asyncContinueInstallation()
                return json.dumps({"result":"installing"})
            elif status == "installed":
                service.start()
                return json.dumps({"result":"installing"})
            elif status == "deleted":
                services.remove(service)
                return json.dumps({"result":"deleted"})
            else:
                return json.dumps({"result":status})
        else:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Revert to previous version
@api.route("/executerevert", methods=["POST"])
def executeRevert():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service != False:
            if repo.isRevertPossible(data.get("service"), service.getInstalledVersion()):
                return json.dumps({"result":service.asyncRevert()})
            else:
                return json.dumps({"error":"ERR_REVERT_NOT_ALLOWED"})
        else:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Check if an update is available
@api.route("/updatecheck", methods=["POST"])
def checkForUpdate():
    data = request.form
    if data.get("apikey") == getApiKey():
        service = getServiceByName(data.get("service"))
        if service == False:
            return json.dumps({"error":"ERR_SERVICE_NOT_FOUND"})
        else:
            update = {"actualVersion":service.getInstalledVersion(),"latestPossible":repo.getLatestCompatible(data.get("service"), service.getInstalledVersion())}
            return json.dumps(update)
    else:
        return json.dumps({"error":"ERR_AUTH"})

# SERVERMANAGER CONTROL
# Servermanager version and available updates
@api.route("/manager", methods=["POST"])
def checkManagerVersion():
    data = request.form
    if data.get("apikey") == getApiKey():
        response = {"actual":config.servermanagerversion}
        if repo.getLatestAvailable("servermanager")["version"] != config.servermanagerversion:
            response["available"] = repo.getLatestAvailable("servermanager")["version"]
        return json.dumps(response)
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Execute a manager update
@api.route("/executemanagerupdate", methods=["POST"])
def executeManagerUpdate():
    data = request.form
    if data.get("apikey") == getApiKey():
        update.managerupdate.installUpdate(data.get("version"))
        return json.dumps({"result":"running"})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Check manager update status
@api.route("/managerupdatecheck", methods=["POST"])
def managerUpdateCheck():
    data = request.form
    if data.get("apikey") == getApiKey():
        return json.dumps({"result":config.servermanagerversion})
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Get license key
@api.route("/licensekey", methods=["POST"])
def licenseKey():
    data = request.form
    if data.get("apikey") == getApiKey():
        return json.dumps({"result":license.getLicenseKey()})
    else:
        return json.dumps({"error":"ERR_AUTH"})


# ENVIRONMENT VARIABLES
# Get a list of all existing environment variables
@api.route("/listenv", methods=["POST"])
def listEnv():
    data = request.form
    if data.get("apikey") == getApiKey():
        return env.getJson()
    else:
        return json.dumps({"error":"ERR_AUTH"})
# Store a new environment variable
@api.route("/storeenv", methods=["POST"])
def storeEnv():
    data = request.form
    if data.get("apikey") == getApiKey():
        for entry in json.loads(data.get("data")):
            env.storeValue(entry["id"], entry["value"], entry["description"], entry["mutable"])
        return json.dumps({"result":"SUCCESS"})
    else:
        return json.dumps({"error":"ERR_AUTH"})

# Create server
if __name__ == "__main__":
    api.run(debug=True, host="192.168.255.255", port=49100, threaded=True)
