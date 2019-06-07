set -ex

# Install the nvme cli
sudo yum install -y nvme-cli

# Install a udev rule that gets triggered when nvme devices are added
sudo cat <<EOF > /etc/udev/rules/999-aws-ebs-nvme.rules
# ebs nvme devices
KERNEL=="nvme[0-9]*n[0-9]*", ENV{DEVTYPE}=="disk", ATTRS{model}=="Amazon Elastic Block Store", PROGRAM="/usr/local/bin/ebs-nvme-mapping /dev/%k", SYMLINK+="%c"
EOF

# Add a script that is called by udev to rename nvme devices
sudo cat <<EOF > /usr/local/bin/ebs-nvme-mapping
#!/bin/bash
#/usr/local/bin/ebs-nvme-mapping
vol=$(/usr/sbin/nvme id-ctrl --raw-binary "${1}" | \
      cut -c3073-3104 | tr -s ' ' | sed 's/ $//g')
vol=${vol#/dev/}
[ -n "${vol}" ] && echo "${vol/xvd/sd} ${vol/sd/xvd}"
EOF

# Set file permissions on helper script
sudo chown root:root /usr/local/bin/ebs-nvme-mapping
sudo chmod 700 /usr/local/bin/ebs-nvme-mapping

# Tell udev to reload its list of rules
sudo udevadm control --reload
