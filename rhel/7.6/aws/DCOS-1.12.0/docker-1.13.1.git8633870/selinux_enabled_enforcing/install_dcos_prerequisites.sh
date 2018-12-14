#!/usr/bin/env bash
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
ExecStart=/usr/bin/dockerd
EOF

sudo yum install -y yum-utils \
    device-mapper-persistent-data \
    lvm2

sudo yum makecache fast

#Installing RH's fork of docker 1.13.1 through rhui-REGION-rhel-server-extras repository.
sudo yum install -y docker --enablerepo=rhui-REGION-rhel-server-extras
sudo ln -s /usr/libexec/docker/docker-runc-current /usr/libexec/docker/docker-runc
sudo ln -s ../../usr/libexec/docker/docker-proxy-current /usr/bin/docker-proxy

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
sudo getent group nogroup || sudo groupadd nogroup
sudo getent group docker || sudo groupadd docker
sudo touch /opt/dcos-prereqs.installed