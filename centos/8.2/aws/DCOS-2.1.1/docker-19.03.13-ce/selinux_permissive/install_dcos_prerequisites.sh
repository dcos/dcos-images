#!/usr/bin/env bash
sudo setenforce permissive && \
sudo sed -i --follow-symlinks 's/^SELINUX=.*/SELINUX=permissive/g' /etc/sysconfig/selinux
sudo tee /etc/yum.repos.d/docker.repo <<-'EOF'
[dockerrepo]
name=Docker CE Stable - $basearch
baseurl=https://download.docker.com/linux/centos/8/$basearch/stable
enabled=yes
gpgcheck=yes
gpgkey=https://download.docker.com/linux/centos/gpg
EOF

sudo mkdir -p /etc/systemd/system/docker.service.d
sudo tee /etc/systemd/system/docker.service.d/override.conf <<- EOF
[Service]
ExecStart=
ExecStart=/usr/bin/dockerd -H fd://
EOF

systemctl disable firewalld

sudo yum remove docker \
                  docker-client \
                  docker-client-latest \
                  docker-common \
                  docker-latest \
                  docker-latest-logrotate \
                  docker-logrotate \
                  docker-engine

sudo yum install -y yum-utils \
  device-mapper-persistent-data \
  lvm2 \
  iptables

# Don't use this repo file because it is not containing centos 8 directories.
#sudo yum-config-manager \
#    --add-repo \
#    https://download.docker.com/linux/centos/docker-ce.repo
sudo yum install -y libseccomp-2.4.1
sudo yum install -y containerd.io-1.3.7
sudo yum install -y docker-ce-19.03.13 docker-ce-cli-19.03.13
sudo rm -rf /var/lib/docker
sudo systemctl start docker
sudo systemctl enable docker

sudo journalctl -xe
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
