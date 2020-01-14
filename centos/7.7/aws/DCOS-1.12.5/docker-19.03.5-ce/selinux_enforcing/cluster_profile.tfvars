#aws_region = "us-west-2"
#aws_availability_zone = "us-west-2a"

aws_bootstrap_instance_type = "m4.xlarge"
aws_master_instance_type = "m4.xlarge"
aws_agent_instance_type = "m4.xlarge"
aws_public_agent_instance_type = "m4.xlarge"

ssh_key_name = "dcos-images"
# Inbound Master Access
admin_cidr = "0.0.0.0/0"

num_of_masters = "1"
num_of_private_agents = "2"
num_of_public_agents = "1"

custom_dcos_download_path = "https://downloads.dcos.io/dcos/testing/1.12.5/dcos_generate_config.sh"
enable_os_setup_script = false

owner = "dcos-images"
expiration = "3h"
