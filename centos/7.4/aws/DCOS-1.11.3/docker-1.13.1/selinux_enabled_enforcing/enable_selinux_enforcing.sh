sudo /sbin/chkconfig --levels 345 setroubleshoot on
sudo reboot

sudo tee /etc/selinux/config <<- EOF
# This file controls the state of SELinux on the system.
# SELINUX= can take one of these three values:
#       enforcing - SELinux security policy is enforced.
#       permissive - SELinux prints warnings instead of enforcing.
#       disabled - No SELinux policy is loaded.
SELINUX=permissive
# SELINUXTYPE= can take one of these two values:
#       targeted - Targeted processes are protected,
#       mls - Multi Level Security protection.
SELINUXTYPE=targeted
EOF

sudo reboot

sudo tee /etc/selinux/config <<- EOF
# This file controls the state of SELinux on the system.
# SELINUX= can take one of these three values:
#       enforcing - SELinux security policy is enforced.
#       permissive - SELinux prints warnings instead of enforcing.
#       disabled - No SELinux policy is loaded.
SELINUX=enforcing
# SELINUXTYPE= can take one of these two values:
#       targeted - Targeted processes are protected,
#       mls - Multi Level Security protection.
SELINUXTYPE=targeted
EOF

reboot

selinux_mode=$(sudo /usr/sbin/getenforce)
echo "SELinux mode is set to '${selinux_mode}'"

if [ "$selinux_mode" != "Enforcing" ]; then
  echo "ERROR: SELinux mode is not set to 'Enforcing'!"
  exit 1
fi
