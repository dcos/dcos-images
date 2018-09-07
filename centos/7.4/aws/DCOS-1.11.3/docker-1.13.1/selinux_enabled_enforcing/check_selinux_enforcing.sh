set -x

selinux_mode=$(sudo /usr/sbin/getenforce)
echo "SELinux mode is set to '${selinux_mode}'"

if [ "$selinux_mode" != "Enforcing" ]; then
  echo "ERROR: SELinux mode is not set to 'Enforcing'!"
  exit 1
fi
