set -ex

## Bind /var/tmp to /tmp
sudo mount -o rw,noexec,nosuid,nodev,bind /tmp/ /var/tmp/
## Remount /tmp
sudo mount -o remount,noexec,nosuid,nodev /tmp
## Remount /dev/shm
sudo mount -o remount,noexec,nosuid,nodev /dev/shm
