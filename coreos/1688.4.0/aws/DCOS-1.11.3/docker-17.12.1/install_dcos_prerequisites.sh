#!/usr/bin/env bash

sudo systemctl disable locksmithd
sudo systemctl stop locksmithd
sudo systemctl restart docker # Restarting docker to ensure its ready. Seems like its not during first usage.

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
