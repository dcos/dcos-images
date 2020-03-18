#!/usr/bin/env bash
sudo setenforce permissive && \
sudo sed -i --follow-symlinks 's/^SELINUX=.*/SELINUX=permissive/g' /etc/sysconfig/selinux

sudo yum install -y yum-utils

sudo yum-config-manager --add-repo https://download.docker.com/linux/centos/docker-ce.repo
sudo yum makecache

sudo yum install -y docker-ce-18.09.1 docker-ce-cli-18.09.1 containerd.io
sudo systemctl enable docker
sudo systemctl start docker

sudo yum install -y wget
sudo yum install -y git
sudo yum install -y unzip
sudo yum install -y curl
sudo yum install -y xz
sudo yum install -y ipset
sudo yum install -y bind-utils
sudo getent group docker || sudo groupadd docker
sudo touch /opt/dcos-prereqs.installed
