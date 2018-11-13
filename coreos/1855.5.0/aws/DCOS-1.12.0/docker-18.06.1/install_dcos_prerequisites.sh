#!/usr/bin/env bash

sudo systemctl disable locksmithd
sudo systemctl stop locksmithd
sudo systemctl restart docker # Restarting docker to ensure its ready. Seems like it's not during first usage.
