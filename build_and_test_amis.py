#!/usr/bin/env python3
import os
import json
import subprocess
import sys
import shutil
import re


VARIABLES_TF = """
variable "aws_default_os_user" {
 type = "map"
   default = {
    {var.os}  = "{ssh_user}"
   }
}

variable "aws_ami" {
 type = "map"
   default = {
    {var.os_var.region} = "{ami}"
  }
}
"""


def get_ami_id(dirname):
    with open(os.path.join(dirname, 'dcos_images.json'), 'r') as f:
        dcos_cloud_images_dict = json.load(f)
        last_published = dcos_cloud_images_dict["last_run_uuid"]
        for build in dcos_cloud_images_dict["builds"]:
            if build["packer_run_uuid"] == last_published:
                ami_map = dict(item.split(":") for item in build["artifact_id"].split(","))
                return ami_map["us-west-2"]


def terraform_add_os(build_dir, tf_dir, platform, vars_string, ami, os_name):
    new_os = os.path.join(tf_dir, 'modules/dcos-tested-aws-oses/platform/cloud/{}/{}'.format(platform, os_name))
    os.makedirs(new_os)
    vars_path = os.path.join(tf_dir, 'modules/dcos-tested-aws-oses/variables.tf')
    with open(vars_path, 'w') as f:
        vars_string = vars_string.replace('{ami}', ami)
        f.write(vars_string)
    shutil.copyfile(os.path.join(build_dir, 'setup.sh'), os.path.join(new_os, 'setup.sh'))


def generate_variables_tf(ssh_user, cluster_profile, platform):
    vars_tf = VARIABLES_TF.replace('{ssh_user}', ssh_user)
    os_name = None
    region = None
    with open(cluster_profile, 'r') as f:
        for line in f.readlines():
            if os_name and region:
                break
            m = re.search('".+"', line)
            if m:
                value = m.group(0)[1:-1]
            else:
                raise Exception('desired_cluster_profile.tfvars syntax error. Bad line: ' + line)
            if not os_name:
                m = re.search('\s*os\s*=', line)
                if m:
                    os_name = value
                    vars_tf = vars_tf.replace('{var.os}', os_name)
            if not region:
                if '{}_region'.format(platform) in line:
                    region = value
    err = ''
    if os_name is None:
        err += 'required os variable not found in desired_cluster_profile.tfvars\n'
    if region is None:
        err += 'required {}_region variable not found in desired_cluster_profile.tfvars'.format(platform)
    if err:
        raise Exception(err)
    vars_tf = vars_tf.replace('{var.os_var.region}', '{}_{}'.format(os_name, region))
    return vars_tf, os_name


def prepare_terraform(build_dir, tf_dir):
    """ Preparing the terraform directory and its variables before attempting to build any AMI with packer, because if
    there's an error with terraform, we want to catch it right from the start and avoid building an AMI (long process)
    for nothing
    """
    platform = build_dir.split('/')[2]
    with open(os.path.join(build_dir, 'packer.json'), 'r') as f:
        ssh_user = json.load(f)['builders'][0]['ssh_username']
    cluster_profile = os.path.join(build_dir, 'desired_cluster_profile.tfvars')
    vars, os_name = generate_variables_tf(ssh_user, cluster_profile, platform)
    init_cmd = 'terraform init -from-module github.com/dcos/terraform-dcos/' + platform
    subprocess.run(init_cmd.split(), check=True, cwd=tf_dir)
    return vars, platform, cluster_profile, os_name, ssh_user


def find_file(name, path):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def update_source_image(build_dir, packer_file):
    os_version_dir = '/'.join(build_dir.split('/')[:2])
    with open(packer_file, 'r') as f:
        content = f.read()
    m = re.search('"source_ami.+', content)
    if not m:
        raise Exception("source_ami field not found in packer.json")
    base_images_file = find_file('base_images.json', os_version_dir)
    if base_images_file is None:
        raise Exception('base_images.json not found')
    with open(base_images_file, 'r') as f:
        ami = json.load(f)['us-west-2']
        content.replace(m.group(0), '"source_ami": "{}",'.format(ami))
    with open(packer_file, 'w') as f:
        f.write(content)


def get_private_ips():
    """ Script to get the private IPs of agents. This script is temporary as this functionality will be added into
    terraform in the near future.
    """
    private_ips_script = """ cat > private-ip.tf <<'EOF'
output "Private Agent Private IPs" {
  value = ["${aws_instance.agent.*.private_ip}"]
}

output "Public Agent Private IPs" {
  value = ["${aws_instance.public-agent.*.private_ip}"]
}

output "Master Private IPs" {
  value = ["${aws_instance.master.*.private_ip}"]
}
EOF
"""
    return private_ips_script


def run_integration_tests(ssh_user, tf_dir):
    """ Running dcos integration tests on terraform cluster.
    """
    output = subprocess.check_output(['terraform', 'output', '-json'], cwd=tf_dir)
    output_json = json.loads(output.decode("utf-8"))
    env_dict = {'MASTER_HOSTS': '', 'PUBLIC_SLAVE_HOSTS': '', 'SLAVE_HOSTS': ''}

    master_public_ip = output_json['Master Public IPs']['value']
    master_private_ips = output_json['Master Private IPs']['value']
    private_agent_private_ips = output_json['Private Agent Private IPs']['value']
    public_agent_private_ips = output_json['Public Agent Private IPs']['value']

    env_dict['MASTER_HOSTS'] = ','.join(m for m in master_private_ips)
    env_dict['SLAVE_HOSTS'] = ','.join(m for m in private_agent_private_ips)
    env_dict['PUBLIC_SLAVE_HOSTS'] = ','.join(m for m in public_agent_private_ips)

    env_string = ' '.join(['{}={}'.format(key, env_dict[key]) for key in env_dict.keys()])

    pytest_cmd = """ bash -c "source /opt/mesosphere/environment.export &&
    cd `find /opt/mesosphere/active/ -name dcos-integration-test* | sort | tail -n 1` &&
    {env} py.test" """.format(env=env_string)
 
    user_and_host = ssh_user + '@' + master_public_ip[0]

    # Running integration tests
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", user_and_host, pytest_cmd], check=True, cwd=tf_dir)


def main(build_dir, tf_dir):
    vars_string, platform, cluster_profile, os_name, ssh_user = prepare_terraform(build_dir, tf_dir)
    print('Building path ' + build_dir)
    packer_file = os.path.join(build_dir, 'packer.json')
    update_source_image(build_dir, packer_file)
    # subprocess.run('packer validate {}'.format(packer_file).split(), check=True, cwd=build_dir)
    # subprocess.run('packer build {}'.format(packer_file).split(), check=True, cwd=build_dir)

    ami = get_ami_id(build_dir)
    terraform_add_os(build_dir, tf_dir, platform, vars_string, ami, os_name)

    shutil.copyfile(cluster_profile, os.path.join(tf_dir, 'desired_cluster_profile.tfvars'))

    # Getting private IPs of all cluster agents.
    subprocess.call(get_private_ips(), shell=True, cwd=tf_dir)

    try:
        subprocess.run('terraform apply -var-file desired_cluster_profile.tfvars --auto-approve'.split(), check=True,
                       cwd=tf_dir)

        # Run DC/OS integration tests.
        run_integration_tests(ssh_user, tf_dir)
    finally:
        # Removing private-ip.tf before destroying cluster.
        subprocess.run(["rm", "private-ip.tf"], check=True, cwd=tf_dir)

        # Whether terraform manages to create the cluster successfully or not, attempt to delete the cluster.
        subprocess.run('terraform destroy -var-file desired_cluster_profile.tfvars --auto-approve'.split(), check=True,
                       cwd=tf_dir)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python build_and_test_amis.py <directory path>.")
        print("The <directory path> specified as an argument should contain all the files necessary to build the AMIs "
              "and launch a terraform cluster. See README for more details.")
        sys.exit(1)
    build_dir = sys.argv[1]
    tf_dir = os.path.join(build_dir, 'temp')
    os.mkdir(tf_dir)
    try:
        main(build_dir, tf_dir)
    finally:
        # whatever happens we want to make sure the terraform directory is deleted. This is convenient for local testing
        if os.path.exists(tf_dir):
            shutil.rmtree(tf_dir, ignore_errors=True)
