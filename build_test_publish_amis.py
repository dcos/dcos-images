#!/usr/bin/env python3

"""Build, Test and Publish AMI for DC/OS Support Qualification.

"""

import argparse
import os
import json
import subprocess
import shutil
import re
import yaml

CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER = 'publish_dcos_images_after'
CONFIG_KEY_TESTS_TO_RUN = 'tests_to_run'

PUBLISH_STEP_NEVER = "never"
PUBLISH_STEP_INTEGRATION_TESTS = "integration_tests"
PUBLISH_STEP_DCOS_INSTALLATION = "dcos_installation"
PUBLISH_STEP_PACKER_BUILD = "packer_build"

TEST_CONFIG_YAML = 'publish_and_test_config.yaml'

# files used in qualification process.

BASE_IMAGES_JSON = 'base_images.json'
BUILD_HISTORY_JSON = 'packer_build_history.json'
CLUSTER_PROFILE_TFVARS = 'desired_cluster_profile.tfvars'
DCOS_IMAGES_YAML = 'dcos_images.yaml'
PACKER_JSON = 'packer.json'
SETUP_SH = 'setup.sh'
TEMPDIR_FOR_TF = 'temp'

DEFAULT_AWS_REGION = 'us-west-2'

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


def _terraform_add_os(build_dir, tf_dir, platform, vars_string, ami, os_name):
    new_os = os.path.join(tf_dir, 'modules/dcos-tested-aws-oses/platform/cloud/{}/{}'.format(platform, os_name))
    os.makedirs(new_os)

    vars_path = os.path.join(tf_dir, 'modules/dcos-tested-aws-oses/variables.tf')

    with open(vars_path, 'w') as f:
        vars_string = vars_string.replace('{ami}', ami)
        f.write(vars_string)

    shutil.copyfile(os.path.join(build_dir, SETUP_SH), os.path.join(new_os, SETUP_SH))


def _generate_variables_tf(ssh_user, cluster_profile, platform):
    vars_tf = VARIABLES_TF.replace('{ssh_user}', ssh_user)

    os_name = None
    region = None

    with open(cluster_profile) as f:
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


def get_ssh_user_from_packer_json(build_dir):
    with open(os.path.join(build_dir, PACKER_JSON)) as f:
        ssh_user = json.load(f)['builders'][0]['ssh_username']
    return ssh_user


def prepare_terraform(build_dir, tf_dir):
    """Preparing the terraform directory and its variables before attempting to build any AMI with packer.

    If there's an error with terraform, we want to catch it right from the start and avoid building an AMI
    (long process) for nothing.

    :param build_dir: Input directory for building DC/OS Image.
    :param tf_dir: Directory for doing terraform operations.
    :return:
    """
    _tf_init_cmd = 'terraform init -from-module github.com/dcos/terraform-dcos/'

    # Our input is assumed in the format.
    # <OS>/<version>/<platform>/<DCOS-version>
    platform = build_dir.split('/')[2]

    ssh_user = get_ssh_user_from_packer_json(build_dir)
    cluster_profile = os.path.join(build_dir, CLUSTER_PROFILE_TFVARS)
    vars, os_name = _generate_variables_tf(ssh_user, cluster_profile, platform)

    init_cmd = _tf_init_cmd + platform
    subprocess.run(init_cmd.split(), check=True, cwd=tf_dir)

    return vars, platform, cluster_profile, os_name


def _find_files_with_name(path, name):
    for root, dirs, files in os.walk(path):
        if name in files:
            return os.path.join(root, name)


def update_source_image_in_packer_json(build_dir):
    # Our input is assumed in the format.
    # <OS>/<version>/<platform>/<DCOS-version>

    os_version_dir = '/'.join(build_dir.split('/')[:2])

    packer_file = os.path.join(build_dir, PACKER_JSON)

    with open(packer_file) as f:
        content = f.read()

    m = re.search('"source_ami.+', content)

    if not m:
        raise ValueError("source_ami field not found in packer.json")

    base_images_file = _find_files_with_name(os_version_dir, BASE_IMAGES_JSON)

    if base_images_file is None:
        raise ValueError("{file} not found".format(file=BASE_IMAGES_JSON))

    with open(base_images_file) as f:
        ami = json.load(f)[DEFAULT_AWS_REGION]
        content.replace(m.group(0), '"source_ami": "{}",'.format(ami))

    with open(packer_file, 'w') as f:
        f.write(content)


def _add_private_ips_to_terraform(tf_dir):
    """ Creates an output file for terraform that will supply private ips for cluster agents. This is temporary it
    should be added permanently in terraform-dcos.
    """
    content = """
    output "Private Agent Private IPs" {
    value = ["${aws_instance.agent.*.private_ip}"]
    }
    
    output "Public Agent Private IPs" {
      value = ["${aws_instance.public-agent.*.private_ip}"]
    }
    
    output "Master Private IPs" {
      value = ["${aws_instance.master.*.private_ip}"]
    }
    """
    with open(os.path.join(tf_dir, 'private-ip.tf'), 'w') as f:
        f.write(content)


def run_integration_tests(ssh_user, tf_dir, tests):
    """Run DCOS Integration tests on Terraform cluster.

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

    tests_string = ' '.join(tests)
    env_string = ' '.join(['{}={}'.format(key, env_dict[key]) for key in env_dict.keys()])

    pytest_cmd = """ bash -c "source /opt/mesosphere/environment.export &&
    cd `find /opt/mesosphere/active/ -name dcos-integration-test* | sort | tail -n 1` &&
    {env} py.test -s -vv {tests_list}" """.format(env=env_string, tests_list=tests_string)

    user_and_host = ssh_user + '@' + master_public_ip[0]

    # Running integration tests
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", user_and_host, pytest_cmd], check=True, cwd=tf_dir)


def publish_dcos_images(build_dir):
    """publish (push) dcos_images.yaml that was generated back to the PR
    running this step before integration tests because passing all tests is not necessarily a requirement
    to qualify and publish images, as flakiness and false negatives can happen"""
    subprocess.run("""git add dcos_images.yaml packer_build_history.json packer.json &&
                   git commit -m "Publish dcos_images.yaml for {}" &&
                   git push -v""".format(build_dir),
                   check=True, cwd=build_dir, shell=True)


def extract_dcos_images(build_dir):
    with open(os.path.join(build_dir, BUILD_HISTORY_JSON)) as f:
        content = json.load(f)

    # TODO (skumaran) - un-magic parsing variables.
    builds = content['builds'][-1]['artifact_id'].split(',')
    builds = {build.split(':')[0]: build.split(':')[1] for build in builds}

    with open(os.path.join(build_dir, DCOS_IMAGES_YAML), 'w') as f:
        f.write(yaml.dump(builds, default_flow_style=False))


def _validate_config(content):
    """
    Validates the qualification config.

    :param content: config file used for validation.
    :return:
    """
    valid_keys = [CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, CONFIG_KEY_TESTS_TO_RUN]

    valid_steps = [PUBLISH_STEP_PACKER_BUILD,
                   PUBLISH_STEP_DCOS_INSTALLATION,
                   PUBLISH_STEP_INTEGRATION_TESTS,
                   PUBLISH_STEP_NEVER]

    _default_publish_dcos_images_after_step = PUBLISH_STEP_DCOS_INSTALLATION

    for k in content:
        if k not in valid_keys:
            raise ValueError("Unrecognized config parameter: {key}".format(key=k))

    if not isinstance(content.get("tests_to_run", []), list):
        raise ValueError("Config parameter 'tests_to_run' value must be a list.")

    step = content.get("publish_dcos_images_after", _default_publish_dcos_images_after_step)

    if step not in valid_steps:
        raise ValueError("Invalid value for config parameter 'publish_dcos_images_after'. Valid values: ".format(
                step, valid_steps))


def _get_config_info(build_dir):
    config_path = os.path.join(build_dir, TEST_CONFIG_YAML)

    # No actions to take by default.
    _default_action = []

    if not os.path.exists(config_path):
        return PUBLISH_STEP_DCOS_INSTALLATION, _default_action

    with open(config_path) as f:
        content = yaml.load(f)
        _validate_config(content)

        return (content.get(CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, PUBLISH_STEP_DCOS_INSTALLATION),
                content.get(CONFIG_KEY_TESTS_TO_RUN, _default_action))


def packer_validate_and_build(build_dir, dry_run, publish_step):
    _PACKER_VALIDATE_COMMAND = "packer validate {packer_file}".format(packer_file=PACKER_JSON)
    _PACKER_BUILD_COMMAND = "packer build {packer_file}".format(packer_file=PACKER_JSON)

    update_source_image_in_packer_json(build_dir)

    subprocess.run(_PACKER_VALIDATE_COMMAND.split(), check=True, cwd=build_dir)

    if not dry_run and publish_step != PUBLISH_STEP_NEVER:
        subprocess.run(_PACKER_BUILD_COMMAND.split(), check=True, cwd=build_dir)
        extract_dcos_images(build_dir)

        if publish_step == PUBLISH_STEP_PACKER_BUILD:
            publish_dcos_images(build_dir)


def setup_terraform(build_dir, tf_dir):
    with open(os.path.join(build_dir, DCOS_IMAGES_YAML)) as f:
        ami = yaml.load(f)[DEFAULT_AWS_REGION]

    vars_string, platform, cluster_profile, os_name = prepare_terraform(build_dir, tf_dir)

    _terraform_add_os(build_dir, tf_dir, platform, vars_string, ami, os_name)

    shutil.copyfile(cluster_profile, os.path.join(tf_dir, CLUSTER_PROFILE_TFVARS))

    _add_private_ips_to_terraform(tf_dir)


def setup_cluster_and_test(build_dir, tf_dir, dry_run, tests, publish_step):
    ssh_user = get_ssh_user_from_packer_json(build_dir)

    tf_plan_cmd = 'terraform plan -var-file desired_cluster_profile.tfvars'
    tf_apply_cmd = 'terraform apply -var-file desired_cluster_profile.tfvars -auto-approve'
    tf_destroy_cmd = 'terraform destroy -var-file desired_cluster_profile.tfvars -auto-approve'
    rm_private_ip_file_cmd = "rm private-ip.tf"

    if dry_run:
        subprocess.run(tf_plan_cmd.split(), check=True, cwd=tf_dir)
        return

    try:
        subprocess.run(tf_apply_cmd.split(), check=True, cwd=tf_dir)

        if publish_step == PUBLISH_STEP_DCOS_INSTALLATION:
            publish_dcos_images(build_dir)

        # Run Integration Tests.
        run_integration_tests(ssh_user, tf_dir, tests)

        if publish_step == PUBLISH_STEP_INTEGRATION_TESTS:
            publish_dcos_images(build_dir)
    finally:
        # Removing private-ip.tf before destroying cluster.
        subprocess.run(rm_private_ip_file_cmd.split(), check=True, cwd=tf_dir)

        # Whether terraform manages to create the cluster successfully or not, attempt to delete the cluster
        subprocess.run(tf_destroy_cmd.split(), check=True, cwd=tf_dir)


def get_tf_build_dir(build_dir):
    tf_build_dir = os.path.join(build_dir, TEMPDIR_FOR_TF)
    os.mkdir(tf_build_dir)
    return tf_build_dir


def execute_qualification_process(build_dir, dry_run, tests, publish_step):
    """Execute DC/OS Qualification process.

    :param build_dir:
    :param tf_dir:
    :param dry_run:
    :param tests:
    :param publish_step:
    :return:
    """
    packer_validate_and_build(build_dir, dry_run, publish_step)

    tf_build_dir = get_tf_build_dir(build_dir)

    try:
        setup_terraform(build_dir, tf_build_dir)
        setup_cluster_and_test(build_dir, tf_build_dir, dry_run, tests, publish_step)
    finally:
        shutil.rmtree(tf_build_dir, ignore_errors=True)


def main(build_dir: str, dry_run: bool, custom_tests: list):
    publish_step, custom_tests_from_config = _get_config_info(build_dir)
    tests_to_run = custom_tests or custom_tests_from_config
    execute_qualification_process(build_dir, dry_run, tests_to_run, publish_step)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build, Test and Qualify DC/OS Image.")

    parser.add_argument(dest="build_dir",
                        required=True,
                        help="The directory that contains all the files necessary as a input to build a DCOS image.")

    parser.add_argument("--dry-run",
                        action="store_true",
                        dest="dry_run",
                        required=False,
                        default=False,
                        help="Dry Run the Build, Test, Qualify Process.\n"
                             "This will exclude running the packer build, creating a terraform cluster "
                             "and running the integration tests.\n" 
                             "This tests the 'packer validate', and 'terraform plan' work on the configuration "
                             "files specified thus validating our configuration and the build process itself.")

    parser.add_argument("-k", dest="custom_tests", default=None, nargs="*", help="Run specific integration tests.")

    args = parser.parse_args()
    main(args.build_dir, args.dry_run, args.custom_tests)
