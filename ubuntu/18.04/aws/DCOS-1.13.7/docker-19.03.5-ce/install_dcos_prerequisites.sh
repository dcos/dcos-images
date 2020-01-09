#!/usr/bin/env bash
sudo sed -i '$ d' /etc/resolv.conf
sudo bash -c 'echo -e "nameserver 8.8.8.8\n" >> /etc/resolv.conf'

sudo tee /etc/modules-load.d/overlay.conf <<-'EOF'
overlay
EOF

sudo apt-get update
sudo apt-get install \
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

sudo apt-get install docker-ce="5:19.03.5~3-0~ubuntu-bionic" docker-ce-cli="5:19.03.5~3-0~ubuntu-bionic" containerd.io

sudo systemctl start docker
sudo systemctl enable docker

sudo apt-get install ntp
sudo systemctl enable ntp
sudo systemctl start ntp
sudo apt-get install wget
sudo apt-get install unzip
sudo apt-get install git
sudo apt-get install ipset

sudo systemctl disable systemd-resolved.service
sudo systemctl stop systemd-resolved.service

sudo rm /etc/resolv.conf && sudo ln -s /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf

sudo touch /opt/dcos-prereqs.installed
