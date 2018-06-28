Change default username

* https://emagalha.es/blog/2018/01/21/customizing-the-default-user-of-an-ubuntu-ami/


Verify what is different in this
--------------------------------

 "us-west-2:ami-d71e55af"

--------

1. Create an AMI using clckwrk image.

2. Dissociate the marketplace code from the image.

3. Create a oracle user.

sudo adduser oracle
sudo su - oracle
mkdir .ssh
chmod 700 .ssh
touch .ssh/authorized_keys
chmod 600 .ssh/authorized_keys

add keys from clckwrk's .ssh/authorized_keys to the previous authorized_keys


4. usermod -aG wheel username

5. Have /etc/rc.local to be something like this

::

    $ cat /etc/rc.local

    #!/bin/bash
    # THIS FILE IS ADDED FOR COMPATIBILITY PURPOSES
    #
    # It is highly advisable to create own systemd services or udev rules
    # to run scripts during boot instead of using this file.
    #
    # In contrast to previous versions due to parallel execution during boot
    # this script will NOT be run after all other services.
    #
    # Please note that you must run 'chmod +x /etc/rc.d/rc.local' to ensure
    # that this script will be executed during boot.


    echo 'Enabling network service'
    chkconfig network on
    echo 'Restarting network service'
    service network restart
    touch /var/lock/subsys/local

    # Add key for oracle user
      curl http://169.254.169.254/latest/meta-data/public-keys/0/openssh-key > /home/oracle/.ssh/authorized_keys
      chown oracle:oracle /home/oracle/.ssh/authorized_keys
      chmod 600 /home/oracle/.ssh/authorized_keys


