#!/usr/bin/env bash
sudo tee /etc/modules-load.d/overlay.conf <<-'EOF'
overlay
EOF

sudo apt-get -y remove docker docker-engine docker.io containerd runc
sudo apt-get -y update
sudo apt-get -y install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg-agent \
    software-properties-common

sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo apt-key fingerprint 0EBFCD88
sudo add-apt-repository \
      "deb [arch=amd64] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) \
      stable"
sudo apt-get update

sudo apt-get -y install docker-ce="5:18.09.9~3-0~ubuntu-xenial" docker-ce-cli="5:18.09.9~3-0~ubuntu-xenial" containerd.io

sudo systemctl start docker
sudo systemctl enable docker

sudo apt-get -y install ntp
sudo systemctl enable ntp
sudo systemctl start ntp
sudo apt-get -y install wget
sudo apt-get -y install unzip
sudo apt-get -y install git
sudo apt-get -y install ipset

sudo ln -s /bin/rm /usr/bin/rm
sudo ln -s /bin/tar /usr/bin/tar
sudo ln -s /bin/ln /usr/bin/ln
sudo ln -s /bin/mkdir /usr/bin/mkdir
sudo ln -s /usr/sbin/useradd /usr/bin/useradd
sudo ln -s /usr/sbin/groupadd /usr/bin/groupadd
sudo ln -s  /bin/systemctl /usr/bin/systemctl

#sudo systemctl disable systemd-resolved.service
#sudo systemctl stop systemd-resolved.service

#sudo rm /etc/resolv.conf && sudo ln -s /run/systemd/resolve/stub-resolv.conf /etc/resolv.conf

sudo touch /opt/dcos-prereqs.installed
