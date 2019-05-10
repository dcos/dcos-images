sudo bash -c "echo 'tmpfs /dev/shm tmpfs defaults,nodev,nosuid,noexec 0 0' >> /etc/fstab"
sudo bash -c "echo 'tmpfs /tmp tmpfs defaults,nodev,nosuid,noexec 0 0' >> /etc/fstab"
sudo bash -c "echo '/tmp /var/tmp none rw,noexec,nosuid,nodev,bind 0 0' >> /etc/fstab"

## Bind /var/tmp to /tmp
sudo mount -o rw,noexec,nosuid,nodev,bind /tmp/ /var/tmp/
## Remount /tmp
sudo mount -o remount,noexec,nosuid,nodev /tmp
## Remount /dev/shm
sudo mount -o remount,noexec,nosuid,nodev /dev/shm
