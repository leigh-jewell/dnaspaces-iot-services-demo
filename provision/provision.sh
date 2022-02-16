#!/bin/bash
# Build and populate the VM: install and/or compile the necessary
# tools needed to run the minimal Flask application with Apache and mod_wsgi.
#
# This script is automatically run the *first time* you issue the command:
#
#    vagrant up
#

# Some convenience variables

APP_NAME="dnaspaces-iot-services-demo"
LOG_BASE="/var/log"
LOG_FILE="$LOG_BASE/$APP_NAME.log"
WWW_ROOT="/var/www/$APP_NAME"
SOURCE_ROOT="/vagrant"
SOURCE_PROVISION="$WWW_ROOT/provision"

# Temporary: Create and perm-fix log file
echo "*** Preparing log file ***"
sudo touch "$LOG_FILE"
sudo chmod 666 "$LOG_FILE"

echo "*** Installing prerequisite packages ***"

sudo apt-get update >> $LOG_FILE 2>&1
sudo apt-get install -yq \
    python3-pip \
    apache2 \
    apache2-dev \
    libapache2-mod-wsgi-py3 >> $LOG_FILE 2>&1

echo "*** Install Python modules ***"
if [ ! -f "/usr/local/venv/$APP_NAME"]
  sudo mkdir "/usr/local/venv/$APP_NAME"
  sudo python3 -m virtualenv "/usr/local/venv/$APP_NAME"
else
  echo "Virtual environment directory exists"
source "/usr/local/venv/$APP_NAME/bin/activate"
if [ ! -f "$WWW_ROOT/requirements.txt" ]; then
  echo "ERROR: pip install requirements file missing." >> "$LOG_FILE" 2>&1
  exit 1
else
  sudo -H pip3 install -r "$WWW_ROOT/requirements.txt">> "$LOG_FILE" 2>&1
fi

echo "*** Adding mod_wsgi config file to Apache modules ***"
if [ ! -f /etc/apache2/mods-available/mod_wsgi.load ]; then
  sudo cp "$SOURCE_PROVISION/mod_wsgi.load" /etc/apache2/mods-available >> "$LOG_FILE" 2>&1
else
  echo "mod_wsgi already exists in Apache modules..skipping."
fi
if [ ! -f /etc/apache2/mods-available/mod_wsgi.load ]; then
  echo "ERROR: file mod_wsgi.load not copied to /etc/apache2/mods-available" >> "$LOG_FILE" 2>&1
  exit 1
fi

echo "*** Creating wwww-data dir for log files ***"
if [! -f "/home/www-data" ]
  sudo mkdir /home/www-data >> $LOG_FILE 2>&1
  sudo chown -R www-data:www-data /home/www-data >> "$LOG_FILE" 2>&1
else
  echo "/home/www-data already exists"
fi
echo "*** Creating virtual host site configuration for Apache ***"
sudo cp -f "$SOURCE_PROVISION/apache_site.conf" "/etc/apache2/sites-available/$APP_NAME.conf" >> "$LOG_FILE" 2>&1
if [ ! -f "/etc/apache2/sites-available/$APP_NAME.conf" ]; then
  echo "ERROR: unable to copy file to /etc/apache2/sites-available/$APP_NAME.conf" >> "$LOG_FILE" 2>&1
  exit 1
fi

sudo a2ensite $APP_NAME.conf >> "$LOG_FILE" 2>&1

echo "*** Restarting Apache to inculde changes ***"
sudo systemctl restart apache2 >> "$LOG_FILE" 2>&1

echo "*** Checking Apache site enabled ***"
if a2query -s | grep -q $APP_NAME; then
   echo "*** Success : Apache site $APP_NAME enabled ***"
else
  echo "ERROR: Apache site $APP_NAME NOT enabled"
  exit 1
fi

echo "*** Checking Apache modules ***"
modules="ssl headers wsgi"
for MODULE in $modules; do
  if a2query -m | grep -q $MODULE; then
     echo "Apache $MODULE enabled" >> "$LOG_FILE" 2>&1
  else
    echo "*** ERROR ***: Apache $MODULE NOT enabled" >> "$LOG_FILE" 2>&1
  fi
done
echo "*** Finished provisioning ***"
