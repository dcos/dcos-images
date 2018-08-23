os = "centos"
user = "centos"
aws_region = "us-west-2"

aws_bootstrap_instance_type = "m3.large"
aws_master_instance_type = "m4.xlarge"
aws_agent_instance_type = "m4.xlarge"
aws_public_agent_instance_type = "m4.xlarge"

ssh_key_name = "dcos-images"
# Inbound Master Access
admin_cidr = "0.0.0.0/0"

num_of_masters = "1"
num_of_private_agents = "5"
num_of_public_agents = "1"
