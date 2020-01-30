#!/usr/bin/env bash
sudo setenforce 1 && \
sudo sed -i --follow-symlinks 's/^SELINUX=.*/SELINUX=enforcing/g' /etc/sysconfig/selinux

yumreposdir="/etc/yum.repos.d/"
sudo mkdir ${yumreposdir}/oldrepos
sudo mv ${yumreposdir}/CentOS-* ${yumreposdir}/oldrepos

sudo tee ${yumreposdir}/centos77-repos.repo <<-'EOF'
[local-base]
name=CentOS Base
baseurl=http://vault.centos.org/7.6.1810/os/$basearch/
gpgcheck=0
enabled=1
[local-updates]
name=CentOS Updates
baseurl=http://vault.centos.org/7.6.1810/updates/$basearch/
gpgcheck=0
enabled=1
[local-extras]
name=CentOS Extras
baseurl=http://vault.centos.org/7.6.1810/extras/$basearch/
gpgcheck=0
enabled=1
[local-docker-ce]
name=Docker Repository
baseurl=https://download.docker.com/linux/centos/7/$basearch/stable
enabled=1
gpgcheck=0
#gpgkey=https://yum.dockerproject.org/gpg
EOF

sudo yum clean all
sudo yum repolist -v

sudo yum install -y yum-utils device-mapper-persistent-data lvm2
sudo yum install -y docker-ce-18.09.9 docker-ce-cli-18.09.9 containerd.io

sudo systemctl start docker
sudo systemctl enable docker
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
