#!/usr/bin/env bash
sudo bash -c 'echo -e "nameserver 8.8.8.8\n" >> /etc/resolv.conf'

sudo tee /etc/yum.repos.d/docker.repo <<-'EOF'
[dockerrepo]
name=Docker Repository
baseurl=https://yum.dockerproject.org/repo/main/centos/7
enabled=1
gpgcheck=1
gpgkey=https://yum.dockerproject.org/gpg
EOF
# sudo yum -y update --exclude="docker-engine*"
sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<- EOF
[Service]
ExecStart=
ExecStart=/usr/bin/docker daemon --storage-driver=overlay
EOF

# Installing RH's fork of Docker 1.13.1
sudo yum install -y docker
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
