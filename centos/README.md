CentOS 7.3 Build Notice
====================

The CentOS 7.3 AMIS with DC/OS pre-requisites installed (located in dcos_images.yaml file) were created manually due to issues with packer since CentOS AMIs are released with an AWS Marketplace code that does not allow one to publish an AMI publicly. The AMI that was used as a base to build these AMIs is the same AMI dcos-launch uses for Centos 7.3.


Volume Mounts Example
=====================

CentOS AMIs also *demonstrate* how to set up volume mounts similar volume mounts setup with the DC/OS Cloudformation templates.

Setting up Volume Mounts are strictly not required for a qualifying an Operating System.  It indicates the possibility of using it in production with having large volumes for storing logs.