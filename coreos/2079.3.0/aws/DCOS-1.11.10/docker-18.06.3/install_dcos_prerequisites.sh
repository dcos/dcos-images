#!/usr/bin/env bash

sudo systemctl disable locksmithd
sudo systemctl stop locksmithd
sudo systemctl mask locksmithd

sudo systemctl disable update-engine # Disabling automatic updates.
sudo systemctl stop update-engine
sudo systemctl mask update-engine

sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<- EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd://
EOF

sudo systemctl restart docker # Restarting docker to ensure its ready. Seems like its not during first usage
