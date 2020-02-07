set -ex

# load the modules
sudo modprobe dm_raid
sudo modprobe raid1

# Load RAID-related kernel modules on boot
sudo bash -c "echo 'dm_raid' >> /etc/modules-load.d/modules.conf"
sudo bash -c "echo 'raid1' >> /etc/modules-load.d/modules.conf"
