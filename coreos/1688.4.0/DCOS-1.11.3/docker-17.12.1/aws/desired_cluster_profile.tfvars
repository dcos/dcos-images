os = "coreos"
user = "core"
aws_region = "us-west-2"
aws_profile = "273854932432_Mesosphere-PowerUser"

aws_bootstrap_instance_type = "m3.large"
aws_master_instance_type = "m4.2xlarge"
aws_agent_instance_type = "m4.2xlarge"
aws_public_agent_instance_type = "m4.2xlarge"

ssh_key_name = "default"
# Inbound Master Access
admin_cidr = "0.0.0.0/0"

dcos_version = "master"
custom_dcos_download = "https://downloads.dcos.io/dcos/stable/dcos_generate_config.sh"

num_of_masters = "1"
num_of_private_agents = "2"
num_of_public_agents = "1"
