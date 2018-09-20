The DC/OS images that were built in this folder were built manually instead of the automated way (creating a PR).
Enabling SELinux requires two reboots, which did not seem to work with packer. Several attempts were made with this PR:
hhttps://github.com/dcos/dcos-images/pull/62

The images were built manually using these instructions:
https://docs.fedoraproject.org/en-US/Fedora/11/html/Security-Enhanced_Linux/sect-Security-Enhanced_Linux-Working_with_SELinux-Enabling_and_Disabling_SELinux.html
Instead of using an AMI from base_images.json as a base image, an AMI from the selinux_disabled directory was used:
https://github.com/dcos/dcos-images/tree/master/centos/7.4/aws/DCOS-1.11.3/docker-1.13.1/selinux_disabled/dcos_images.yaml
