#!/usr/bin/env bash

# SchoolConnect Server-Installer
# © 2019 Johannes Kreutz.

# Check for root rights
if [[ $EUID > 0 ]]; then
  echo "To install the SchoolConnect Server-Manager, you have to run this as root (sudo is fine)."
  exit
fi

# Check if the servermanager is already installed
if [ -d "servermanager" ]; then
  if [ -f "servermanager/.SchoolConnectSetupDone" ]; then
    whiptail --title "ALREADY INSTALLED" --msgbox "It seems like the SchoolConnect Server-Manager is already installed. Please delete 'servermanager/.SchoolConnectSetupDone' if you are shure it is not installed yet." 10 80
    exit
  fi
fi

# Check for minimal dependencies (graphical install)
if ! command -v whiptail > /dev/null; then
  echo "Installing some dependencies first..."
  apt install -y whiptail sudo
fi

# Begin graphical install
whiptail --title "WELCOME TO THE SCHOOLCONNECT SERVER-MANAGER INSTALLER!" --msgbox "This script will install the SchoolConnect Server-Manager on your machine. Press Return to begin!" 10 80

# Ask and store required settings
until ! [ -z "$SLAPD_PASSWORD" ]; do
  SLAPD_PASSWORD=$(whiptail --title "SLAPD ROOT PASSWORD" --inputbox "First, please enter a root password for the slapd-service (OpenLDAP). WARNING! Anyone with this password can read and change all user data. Keep this password safe, you will need it if something fails!" 10 80 "" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$SLAPD_PASSWORD" ]; then
    whiptail --title "INPUT VERIFICATION ERROR" --msgbox "Empty passwords are not allowed. Please enter a password." 10 80
  fi
done
until ! [ -z "$MYSQL_PASSWORD" ]; do
  MYSQL_PASSWORD=$(whiptail --title "MYSQL ROOT PASSWORD" --inputbox "Now, please enter a root password for the mysqld-service (MySQL Database). WARNING! Anyone with this password can read and change all configuration data, as well as the credentials of the emergency admin account. Keep this password safe, you will need it if something fails!" 10 80 "" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$MYSQL_PASSWORD" ]; then
    whiptail --title "INPUT VERIFICATION ERROR" --msgbox "Empty passwords are not allowed. Please enter a password." 10 80
  fi
done
until ! [ -z "$SLAPD_ORGANIZATION" ]; do
  SLAPD_ORGANIZATION=$(whiptail --title "SLAPD ORGANIZATION" --inputbox "Slapd needs the name of your organization. We recommend you using the name of your school." 10 80 "" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$SLAPD_ORGANIZATION" ]; then
    whiptail --title "INPUT VERIFICATION ERROR" --msgbox "This value is required." 10 80
  fi
done
PREV_USERDATA=""
until ! [ -z "$USERDATA" ]; do
  USERDATA=$(whiptail --title "USER DATA STORAGE" --inputbox "Where do you want to store user data? Please type an absolute path, for example to the mount point of your data disks. We highly recommend to create regular backups of this location!" 10 80 "$PREV_USERDATA" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$USERDATA" ]; then
    whiptail --title "INPUT VERIFICATION ERROR" --msgbox "This value is required." 10 80
  fi
  if [ ! -d "$USERDATA" ]; then
    if (whiptail --title "DIRECTORY NOT FOUND" --yesno "The directory you entered does not exist. Should we create it?." 10 80); then
      if mkdir -p "$USERDATA" ; then
        whiptail --title "DIRECTORY CREATION" --msgbox "User data directory successfully created." 10 80
      else
        whiptail --title "DIRECTORY CREATION FAILED" --msgbox "Unable to create the user data directory. Check permissions." 10 80
        PREV_USERDATA=$USERDATA
        unset USERDATA
      fi
    else
      PREV_USERDATA=$USERDATA
      unset USERDATA
    fi
  fi
done
# Remove trailing slash if existing
USERDATA=$(echo $USERDATA | sed 's:/*$::')

# Explain optional settings
whiptail --title "OPTIONAL SETTINGS" --msgbox "The following settings already have good default values. You can change them, but we don't recommend it unless you know what you are doing." 10 80

# Ask and store optional settings
until ! [ -z "$SLAPD_DOMAIN0" ]; do
  SLAPD_DOMAIN0=$(whiptail --title "SLAPD TOPLEVEL DOMAIN" --inputbox "Slapd needs a top level domain. Everything will be stored under this key, but the user doesn't see it." 10 80 "local" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$SLAPD_DOMAIN0" ]; then
    if (whiptail --title "INPUT VERIFICATION ERROR" --yesno "Even if changing is optional, this value is required. Do you want to use the default? (No takes you back to the input screen.)" 10 80) then
      SLAPD_DOMAIN0="local"
    fi
  fi
done
until ! [ -z "$SLAPD_DOMAIN1" ]; do
  SLAPD_DOMAIN1=$(whiptail --title "SLAPD SECOND LEVEL DOMAIN" --inputbox "Slapd also needs a second level domain. A lot will be stored under this key, but the user doesn't see it." 10 80 "schoolconnect" 3>&1 1>&2 2>&3)
  exitstatus=$?
  if ! [ $exitstatus = 0 ]; then
    echo "User canceled setup. Nothing has been installed yet, so it's safe to start again."
    exit
  fi
  if [ -z "$SLAPD_DOMAIN1" ]; then
    if (whiptail --title "INPUT VERIFICATION ERROR" --yesno "Even if changing is optional, this value is required. Do you want to use the default? (No takes you back to the input screen.)" 10 80) then
      SLAPD_DOMAIN1="schoolconnect"
    fi
  fi
done

whiptail --title "FINISH INSTALLATION" --msgbox "All configuration values are set. Now I'll install the required dependencies, download the server manager files and install them. Relax for some minutes." 10 80

# Create a user for the server manager
adduser --system --shell /bin/bash --gecos "User running the SchoolConnect Server-Manager" --group --disabled-password servermanager

# Allow the servermanager user to start and stop its service
if [ -f "/tmp/sudoers.sctmp" ]; then
    rm /tmp/sudoers.sctmp
fi
cp /etc/sudoers /tmp/sudoers.sctmp
if ! grep -qxF "Cmnd_Alias SERVERMANAGER_CONTROL = /bin/systemctl restart servermanager.service" /tmp/sudoers.sctmp; then
    echo "Cmnd_Alias SERVERMANAGER_CONTROL = /bin/systemctl restart servermanager.service" >> /tmp/sudoers.sctmp
fi
if ! grep -qxF "servermanager ALL=(ALL) NOPASSWD: SERVERMANAGER_CONTROL" /tmp/sudoers.sctmp; then
    echo "servermanager ALL=(ALL) NOPASSWD: SERVERMANAGER_CONTROL" >> /tmp/sudoers.sctmp
fi
if ! grep -qxF "Cmnd_Alias SERVERMANAGER_VOLUMEBACKUP = /usr/local/bin/servermanager/volumebackup.py" /tmp/sudoers.sctmp; then
    echo "Cmnd_Alias SERVERMANAGER_VOLUMEBACKUP = /usr/local/bin/servermanager/volumebackup.py" >> /tmp/sudoers.sctmp
fi
if ! grep -qxF "servermanager ALL=(ALL) NOPASSWD: SERVERMANAGER_VOLUMEBACKUP" /tmp/sudoers.sctmp; then
    echo "servermanager ALL=(ALL) NOPASSWD: SERVERMANAGER_VOLUMEBACKUP" >> /tmp/sudoers.sctmp
fi
visudo -c -f /tmp/sudoers.sctmp
if [ "$?" -eq "0" ]; then
    cp /tmp/sudoers.sctmp /etc/sudoers
else
    deluser servermanager
    echo "Unable to modify sudoers file. Exiting."
    exit 1
fi
rm /tmp/sudoers.sctmp

# Install dependencies
apt install -y python3 git docker docker.io python3-pip python3-flask python3-docker

# Allow servermanager to control docker
usermod -a -G docker servermanager

# Download the server manager files and extract them
wget -O servermanager_latest.tar.gz https://github.com/philleconnect/ServerManager/releases/download/1.0.0/servermanager.tar.gz
tar -zxf servermanager_latest.tar.gz --directory /usr/local/bin/
rm servermanager_latest.tar.gz

# Create configuration folder
mkdir /etc/servermanager

# Create container storage
mkdir /var/lib/servermanager
mkdir /var/lib/servermanager/services
mkdir /var/lib/servermanager/services/buildcache

# Install python modules for servermanager user
#su servermanager -c "pip3 install docker"
#su servermanager -c "pip3 install flask"

# Grant privileges for config and storage folders
chown -R servermanager:servermanager /etc/servermanager
chown -R servermanager:servermanager /var/lib/servermanager
chown -R servermanager:servermanager /usr/local/bin/servermanager
chown root:root /usr/local/bin/servermanager/volumebackup.py
chmod 755 /usr/local/bin/servermanager/volumebackup.py

# Install a systemd init script for the server manager
cat > /etc/systemd/system/servermanager.service <<EOF
[Unit]
Description=SchoolConnect Server Manager
After=syslog.target

[Service]
Type=simple
User=servermanager
Group=servermanager
WorkingDirectory=/usr/local/bin/servermanager
ExecStart=/usr/local/bin/servermanager/servermanager.py
SyslogIdentifier=servermanager
StandardOutput=syslog
StandardError=syslog
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# Write user settings to file
ENVVARS="{\"SLAPD_PASSWORD\":{\"value\":\"$SLAPD_PASSWORD\",\"description\":\"Root-Passwort für den LDAP-Server.\",\"mutable\":false},\"MYSQL_ROOT_PASSWORD\":{\"value\":\"$MYSQL_PASSWORD\",\"description\":\"Root-Passwort für den MySQL-Server.\",\"mutable\":false},\"SLAPD_ORGANIZATION\":{\"value\":\"$SLAPD_ORGANIZATION\",\"description\":\"Organisations-Kennung in der LDAP-Struktur.\",\"mutable\":false},\"USERDATA\":{\"value\":\"$USERDATA\",\"description\":\"Pfad zum Speicherort für Benutzerdaten.\",\"mutable\":true},\"SLAPD_DOMAIN0\":{\"value\":\"$SLAPD_DOMAIN0\",\"description\":\"Top-Level-Domain für den LDAP-Server.\",\"mutable\":false},\"SLAPD_DOMAIN1\":{\"value\":\"$SLAPD_DOMAIN1\",\"description\":\"Second-Level-Domain für den LDAP-Server.\",\"mutable\":false}}"

echo "$ENVVARS" > /etc/servermanager/env.json
chown servermanager:servermanager /etc/servermanager/env.json

# Create folder structure if not existing in userdata directory
mkdir -p $USERDATA/deleted
mkdir -p $USERDATA/users
mkdir -p $USERDATA/shares
mkdir -p $USERDATA/images
mkdir -p $USERDATA/updates
mkdir -p $USERDATA/updates/drivers
mkdir -p $USERDATA/updates/images
mkdir -p $USERDATA/shares/roomExchange
mkdir -p $USERDATA/shares/schoolExchange
mkdir -p $USERDATA/shares/schoolTemplate
mkdir -p $USERDATA/shares/teacherExchange
mkdir -p $USERDATA/shares/teacherTemplate
mkdir -p $USERDATA/PreviousVersions

# Start the server manager manually with firstsetup parameter (takes some time, will build containers here)
echo "Building containers. This might take a while..."
su servermanager -c "python3 /usr/local/bin/servermanager/servermanager.py firstsetup"

# Create loopback IP so the pc_admin container can connect to the servermanager
cat << EOF >> /etc/netplan/40-servermanager-loopback.yaml
network:
  version: 2
  renderer: networkd
  ethernets:
    lo:
      match:
        name: lo
      addresses: [ 192.168.255.255/32 ]
EOF
netplan generate
netplan apply

# Start the server manager via systemd
systemctl enable servermanager
systemctl start servermanager

# Finalize
touch /etc/servermanager/.ServerManagerSetupDone
whiptail --title "INSTALLATION SUCCEDED" --msgbox "The SchoolConnect Server-Manager has been successfully installed on your server. We will now start it, so you can finish the setup in your web browser. Simply go to http://YOUR_IP:84" 10 80
