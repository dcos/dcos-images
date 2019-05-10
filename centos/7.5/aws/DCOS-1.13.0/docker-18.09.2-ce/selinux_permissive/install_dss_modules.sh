## Adding raid1 & dm_raid modules
sudo curl https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/i915/kbl_guc_ver9_14.bin -o kbl_guc_ver9_14.bin
sudo curl https://git.kernel.org/pub/scm/linux/kernel/git/firmware/linux-firmware.git/tree/i915/bxt_guc_ver8_7.bin -o bxt_guc_ver8_7.bin
sudo mkdir -p /lib/firmware/i915
sudo cp kbl_guc_ver9_14.bin /lib/firmware/i915/kbl_guc_ver9_14.bin
sudo cp bxt_guc_ver8_7.bin /lib/firmware/i915/bxt_guc_ver8_7.bin

# load the modules
sudo modprobe dm_raid raid1

# Load RAID-related kernel modules on boot
sudo bash -c "echo 'dm_raid' >> /etc/modules-load.d/modules.conf"
sudo bash -c "echo 'raid1' >> /etc/modules-load.d/modules.conf"
