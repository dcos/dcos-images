# dcos-images

The reference for DC/OS images and how to build them.  
The goal of this repo is to standardize, across all DC/OS users and developers, the usage and build process of OS cloud
images to run DC/OS.

## Which DC/OS image should I use?
Look for the dcos_images.yaml file in the directory path that matches your requirements.  
Example: [centos/7.4/aws/DCOS-1.11.3/docker-1.13.1/dcos_images.yaml](https://github.com/dcos/dcos-images/blob/master/centos/7.4/aws/DCOS-1.11.3/docker-1.13.1/dcos_images.yaml).

## How can I see a high-level view of what we support?
1. ```git clone https://github.com/dcos/dcos-images.git ~/dcos-images```
2. ```brew install tree``` or ```apt install tree```
3. ```cd ~/dcos-images```
4. ```tree```

There's also a [DC/OS Platform Version Compatibility Matrix](https://docs.mesosphere.com/version-policy/#dcos-platform-version-compatibility-matrix)

## How to build new DC/OS images  
For the simplest use case, all it takes to trigger a build for new DC/OS images is creating a pull request with changes
to either an install_dcos_prerequisites.sh file or packer.json file.  
![flow-chart](flow-diagram.png)  
To modify the following chart, go to [draw.io](https://www.draw.io/) and import draw-io-diagram.xml (located at the root level of this repo)  
[See diagram footnotes for help](#diagram-footnotes)

### Building DC/OS images for a new sa
All the files required to build new DC/OS images are in the yellow-colored boxes in the diagram above   
If you're adding a new operating system, you'll need to create all these files. You should definitely use existing ones
as a starting point.  
Let's go over each one:

- **base_images.json**  
Contains images published directly by the OS providers (CoreOS, CentOS, etc.). You can usually find them on the
provider's website. For example, you can find CoreOS AMIs [here](https://coreos.com/os/docs/latest/booting-on-ec2.html)

- **install_dcos_prerequisites.sh**  
Script that will run and be baked on top base images, which will form new images called a DC/OS images. 

- **packer.json**  
Packer configuration to build DC/OS images. Base images and install_dcos_prerequisites.sh are some of its inputs.

- **desired_cluster_profile.tfvars**  
Configuration for the terraform cluster that will be created using new DC/OS images. This cluster will be used to install
and test DC/OS with the new images.

- **publish_and_test_config.yaml**  
Determines what is required for newly-built images to be commited back to a pull request by jenkins. Also determines
what tests are ran for on a pull request. [See this example](https://github.com/dcos/dcos-images/blob/master/oracle-linux/7.4/aws/DCOS-1.11.3/docker-1.13.1/publish_and_test_config.yaml#L1).
You can specify the field 'publish_dcos_images_after' with possible values: 'packer_build', 'dcos_installation',
'integration_tests' and 'never'. For example, if I want jenkins to push the newly-built DC/OS AMIs to my pull request as
soon as they are built by packer, I would specify 'packer_build'. If I want more confidence and want to make sure
a cluster can successfully spin up and install DC/OS by using this new image, I would specify 'dcos_installation'. That
is the default option. The 'never' is a bit different in the way that not only does it never commit the images back to
the pull request, but it also skips building them at all. This would be to only install DC/OS and run tests against the
current images. The 'tests_to_run' field allows you to run only specific integration tests. If you omit this field, they
will all run.

- **setup.sh**  
Unlike install_dcos_prerequisites.sh, this script won't be baked in DC/OS images. Instead it will only be ran by
terraform when the cluster comes up for a pull request. This can be useful for something that needs to be done on every
boot.

As soon as a pull request is created, if either an install_dcos_prerequisites.sh file or packer.json files are changed,
the appropriate job will be triggered to build, test and publish new AMIs. If none of these two file types are changed,
there will only be a dry run to check that the Jenkinsfile and build_test_publish_amis.py work properly.  
When images are built, jenkins will commit them back to the pull request as a dcos_images.yaml file. Jenkins will commit
those images right after they are built, after the cluster successfully launches, after the tests run successfully or
never, depending on your publish_and_test_config.yaml. That commit will trigger a new jenkins build because of the
webhook, but the Jenkinsfile will detect it and exit immediately with success. We don't want to lose the link to the real
job that is still running the tests or creating a cluster, so jenkins will also comment on the pull request the link to
that job. Depending on the results of that job, it will be up to you to judge if the results are good enough to merge
the pull request and new DC/OS images in the repo.

### Diagram footnotes
__*1__: install_dcos_prerequisites.sh is directly referenced inside of packer.json

__*2__: base_images.json is NOT directly referenced in packer.json. The source_image field inside of packer.json matches
one of the images inside the base_image.json that existed at the time of the last packer build for that packer.json.
That base_images.json may or may not be the same as the current one.  
Before running a packer build, build_test_publish_amis.py will replace whatever source_image the packer.json specifies
with the current us-west-2 image in base_images.json

__*3__: In the case where we just want to test the image without rebuilding a new one, we can configure
publish_and_test_config.yaml to skip the packer build by specifying the field 'publish_dcos_images_after: never'
[as seen here](https://github.com/dcos/dcos-images/blob/master/oracle-linux/7.4/aws/DCOS-1.11.3/docker-1.13.1/publish_and_test_config.yaml#L2).
This can be especially useful when a new pull request is created, several images are built, but some flaky integration tests fail.
In that scenario, we might want to rerun the tests against those new images, in which case we would want to avoid
rebuilding identical images to test against.

__*4__: The contents of setup.sh will not be baked into the resulting images DC/OS images. Instead, terraform will run that
script only when a cluster is created with those DC/OS images.

__*5__: More test suites will be added in the future, such as framework tests. Only minor modifications will need to be made
in build_test_publish_amis.py. Which integration tests are ran can be configured in publish_and_test_config.yaml
by specifying the field 'tests_to_run' and a list of values [as seen here](https://github.com/dcos/dcos-images/blob/master/oracle-linux/7.4/aws/DCOS-1.11.3/docker-1.13.1/publish_and_test_config.yaml#L4).
If you want to run all the tests, simply remove that field.

__*6__: By default, if the terraform cluster launches successfully with the newly built images, those images will be
committed back to the repo. However, this is configurable. You can decide that the images should be committed to the
repo right after they are built, after they successfully pass the tests, or never committed at all. This can be
configured in publish_and_test_config.yaml with the field 'publish_dcos_images_after' [as seen here](https://github.com/dcos/dcos-images/blob/master/oracle-linux/7.4/aws/DCOS-1.11.3/docker-1.13.1/publish_and_test_config.yaml#L1).  
IMPORTANT: this new commit will retrigger the pull request and make the status check go green immediately. This does NOT mean the
cluster created successfully or the tests successfully passed. It depends on publish_dcos_images_after field inside the 
the publish_and_test_config.yaml. You will need to follow the link to the initial build that gets posted on the pull
request as a comment. See *7.

__*7__: The link to the initial jenkins build will be posted as a comment on the pull request so that it can be found easily
after mesosphere_jenkins causes the pull request to trigger a new build by pushing a commit. Before merging a pull
request that creates new DC/OS images, you should always follow the initial link and check the status of the terraform
cluster creation and integration tests run. Typically, users would want mesosphere_jenkins to commit dcos_images.yaml
after the terraform cluster creates, then follow the link to the initial jenkins build, decide if enough tests pass to
qualify the new operating system, then either merge the pull request, retrigger the tests or update the pull request with
bug fixes. If they just want to retrigger the tests due to potential test flakiness, they should push a new commit to
do so, which would include a change to publish_and_test_config.yaml with the field 'publish_dcos_images_after: never' to
avoid rebuilding identical new images.
