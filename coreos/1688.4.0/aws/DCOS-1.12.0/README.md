Core OS 1688.4.0
----------------

* [aws/coreos_production_ami_all.json](aws/coreos_production_ami_all.json) retrieved from http://stable.release.core-os.net/amd64-usr/1688.4.0/
* [aws/install_dcos_prerequisites.sh](aws/install_dcos_prerequisites.sh) is the DC/OS pre-requisite script which is required for installing DC/OS on Core OS 1688.4.0
* [aws/dcos_images.yaml](aws/dcos_images.yaml) is the DC/OS Cloud Image AMI for the Base Operating System, Core OS 1688.4.0. This has the pre-requisites installed, and can be used directly with provisioners like terraform.
