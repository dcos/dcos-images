Core OS
-------


This directory has information on.

* Base AMI images
* Pre-requisite scripts for DC/OS that can be installed on top of Base AMI.
* DCOS Ready AMI images that is Base AMI + Pre-Requisite scripts already installed in them.



1235.12.0
---------

[Base AMI](1235.12.0/aws/coreos_production_ami_all.json) information retrieved from http://stable.release.core-os.net/amd64-usr/1235.12.0/

835.13.0
--------

[Base AMI](835.13.0/aws/coreos_production_ami_all.json) retrieved from http://stable.release.core-os.net/amd64-usr/835.13.0/


1688.4.0
--------

* [1688.4.0/aws/coreos_production_ami_all.json](1688.4.0/aws/coreos_production_ami_all.json) retrieved from http://stable.release.core-os.net/amd64-usr/1688.4.0/
* [1688.4.0/aws/install_dcos_prerequisites.sh](1688.4.0/aws/install_dcos_prerequisites.sh) is the DC/OS pre-requisite script has is required for installing DC/OS on Core OS 1688.4.0
* [1688.4.0/aws/dcos_cloud_images_ami.json](1688.4.0/aws/dcos_cloud_images_ami.json) is the DC/OS Cloud Image AMI for the Base Operating System Core OS 1688.4.0. This has the pre-requisites installed can be used directly with provisioners like terraform.


AMI Builder
-----------

* https://www.packer.io/docs/builders/amazon-ebs.html

