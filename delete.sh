#!/usr/bin/env bash

# SchoolConnect ServerManager delete script
# © 2019 Johannes Kreutz.

# Check for root rights
if [[ $EUID > 0 ]]; then
  echo "To delete the SchoolConnect Server-Manager, you have to run this as root (sudo is fine)."
  exit
fi

# Stop service
systemctl stop servermanager

# Delete all docker stuff
su servermanager -c "python3 /usr/local/bin/servermanager/dockerdelete.py yes"

# Delete everything
rm -R /etc/servermanager
rm -R /usr/local/bin/servermanager
rm -R /var/lib/servermanager
rm -R /etc/netplan/40-servermanager-loopback.yaml
netplan generate
netplan apply
systemctl disable servermanager
rm /etc/systemd/system/servermanager.service
deluser servermanager
