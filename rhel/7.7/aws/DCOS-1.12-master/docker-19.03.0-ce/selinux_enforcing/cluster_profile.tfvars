aws_region = "us-west-2"

aws_bootstrap_instance_type = "m5.large"
aws_master_instance_type = "m5.xlarge"
aws_agent_instance_type = "m5.xlarge"
aws_public_agent_instance_type = "m5.xlarge"

ssh_key_name = "dcos-images"
# Inbound Master Access
admin_cidr = "0.0.0.0/0"

num_of_masters = "1"
num_of_private_agents = "2"
num_of_public_agents = "1"

custom_dcos_download_path = "https://downloads.dcos.io/dcos/testing/1.12/commit/c452bdff5ca3020fc43588a86b280582ea35a88a/dcos_generate_config.sh"
enable_os_setup_script = false

owner = "dcos-images"
expiration = "2h"
