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

custom_dcos_download_path = "https://downloads.dcos.io/dcos/stable/1.12.3/dcos_generate_config.sh"
tags={owner = "gauri", expiration = "1h"}
enable_os_setup_script = false