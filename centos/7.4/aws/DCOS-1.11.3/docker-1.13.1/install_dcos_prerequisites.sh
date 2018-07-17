#!/usr/bin/env bash
sudo setenforce 0 && \
sudo sed -i --follow-symlinks 's/^SELINUX=.*/SELINUX=disabled/g' /etc/sysconfig/selinux

# DC/OS pre-reqs from dcos/dcos cloud images.

# Install base packages

sudo yum --nogpgcheck -t -y groupinstall core
sudo yum --nogpgcheck -t -y install openssh-server grub2 tuned kernel chrony
sudo yum --nogpgcheck -t -y install cloud-init cloud-utils-growpart
sudo yum  -C -t -y remove NetworkManager firewalld --setopt="clean_requirements_on_remove=1"

# Install docker 
sudo tee /etc/yum.repos.d/docker.repo <<-'EOF'
[dockerrepo]
name=Docker Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/7
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
EOF

sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<- EOF
[Service]
ExecStart=
ExecStart=/usr/bin/docker daemon --storage-driver=overlay
EOF
sudo yum install -y docker-engine-1.13.1
sudo systemctl start docker
sudo systemctl enable docker

# Install other pre-requisites

sudo yum install -y wget
sudo yum install -y git
sudo yum install -y unzip
sudo yum install -y curl
sudo yum install -y xz
sudo yum install -y ipset
sudo yum install -y ntp

sudo systemctl enable ntpd
sudo systemctl start ntpd

sudo getent group nogroup || sudo groupadd nogroup
sudo getent group docker || sudo groupadd docker

sudo touch /opt/dcos-prereqs.installed
