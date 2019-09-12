#!/usr/bin/env bash

# SELinux is disabled by default.
# sudo apt-get update

sudo bash -c 'echo -e "nameserver 8.8.8.8\n" >> /etc/resolv.conf'

sudo apt-get install -y \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -

sudo add-apt-repository \
   "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
   $(lsb_release -cs) \
   stable"

sudo apt-get install -y docker-ce=5:18.09.3~3-0~ubuntu-bionic docker-ce-cli=5:18.09.3~3-0~ubuntu-bionic containerd.io

sudo apt-get install -y wget
sudo apt-get install -y git
sudo apt-get install -y unzip
sudo apt-get install -y curl
sudo apt-get install -y xz-utils
sudo apt-get install -y ipset
sudo apt-get install -y bind9
sudo apt-get install -y ntp
sudo systemctl enable ntp
sudo systemctl start ntp
sudo getent group nogroup || sudo groupadd nogroup
sudo getent group docker || sudo groupadd docker
sudo touch /opt/dcos-prereqs.installed
