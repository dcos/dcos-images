#!/usr/bin/env bash

# This works around https://github.com/coreos/bugs/issues/426
mkdir -p /etc/systemd/system/sshd.service.d
touch /etc/systemd/system/sshd.service.d/override.conf
echo '[Service]' >> /etc/systemd/system/sshd.service.d/override.conf
echo 'Restart=always' >> /etc/systemd/system/sshd.service.d/override.conf
# Without this we get:
# sshd.service: Start request repeated too quickly.
# Failed to start OpenSSH server daemon.
# sshd.service: Unit entered failed state.
# sshd.service: Failed with result 'start-limit-hit'.
echo 'RestartSec=3s' >> /etc/systemd/system/sshd.service.d/override.conf


cat<<EOF > /etc/rc.local
#!/bin/sh -e
#
# rc.local
#
# This script is executed at the end of each multiuser runlevel.
# Make sure that the script will "exit 0" on success or any other
# value on error.
#
# In order to enable or disable this script just change the execution
# bits.
#
# By default this script does nothing.
systemctl disable locksmithd
systemctl stop locksmithd
systemctl mask locksmithd
systemctl disable update-engine # Disabling automatic updates.
systemctl stop update-engine
systemctl mask update-engine
systemctl restart docker # Restarting docker to ensure its ready. Seems like its not during first usage
exit 0
EOF