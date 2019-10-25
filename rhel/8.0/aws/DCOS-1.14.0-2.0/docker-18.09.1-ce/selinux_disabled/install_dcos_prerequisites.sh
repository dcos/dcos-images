#!/usr/bin/env bash
sudo setenforce 0 && \
sudo sed -i --follow-symlinks 's/^SELINUX=.*/SELINUX=disabled/g' /etc/sysconfig/selinux

sudo sed -i '$ d' /etc/resolv.conf
sudo bash -c 'echo -e "nameserver 8.8.8.8\n" >> /etc/resolv.conf'

sudo yum install -y yum-utils

sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum makecache

sudo yum install -y --nobest docker-ce docker-ce-cli containerd.io
sudo systemctl enable docker
sudo systemctl start docker

sudo yum install -y wget
sudo yum install -y git
sudo yum install -y unzip
sudo yum install -y curl
sudo yum install -y xz
sudo yum install -y ipset
sudo yum install -y bind-utils
sudo yum install -y ntp
sudo systemctl enable ntpd
sudo systemctl start ntpd
sudo getent group docker || sudo groupadd docker
sudo touch /opt/dcos-prereqs.installed
