#!/usr/bin/env python3
import argparse
import copy
import json
import os
import re
import shutil
import subprocess
import yaml
import requests
import traceback

CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER = 'publish_dcos_images_after'
CONFIG_KEY_TESTS_TO_RUN = 'tests_to_run'
CONFIG_KEY_RUN_FRAMEWORK_TESTS = 'run_framework_tests'
CONFIG_KEY_RUN_INTEGRATION_TESTS = 'run_integration_tests'

PUBLISH_STEP_NEVER = "never"
PUBLISH_STEP_INTEGRATION_TESTS = "integration_tests"
PUBLISH_STEP_DCOS_INSTALLATION = "dcos_installation"
PUBLISH_STEP_PACKER_BUILD = "packer_build"

TEST_CONFIG_YAML = 'publish_and_test_config.yaml'

TERRAFORM_DCOS_VERSION_PIN = "b480e9384127b1ac778e23ecb896315f0ed0df6a"

# files used in qualification process.

BASE_IMAGES_JSON = 'base_images.json'
BUILD_HISTORY_JSON = 'packer_build_history.json'
CLUSTER_PROFILE_TFVARS = 'cluster_profile.tfvars'
DCOS_IMAGES_YAML = 'dcos_images.yaml'
PACKER_JSON = 'packer.json'
SETUP_SH = 'setup.sh'
TEMPDIR_FOR_TF = 'temp'

DEFAULT_AWS_REGION = 'us-west-2'


def get_ssh_user_from_packer_json(build_dir):
    with open(os.path.join(build_dir, PACKER_JSON)) as f:
        ssh_user = json.load(f)['builders'][0]['ssh_username']
    return ssh_user


def prepare_terraform(build_dir, tf_dir, ami, ssh_user):
    """Preparing the terraform directory and its variables before attempting to build any AMI with packer.

    If there's an error with terraform, we want to catch it right from the start and avoid building an AMI
    (long process) for nothing.

    :param build_dir: Input directory for building DC/OS Image.
    :param tf_dir: Directory for doing terraform operations.
    :param ami: AWS AMI to use for the instances.
    :param ssh_user: ssh_user for the AMI
    :return:
    """
    _tf_init_cmd = 'terraform init -from-module github.com/dcos/terraform-dcos?ref={}/'.format(TERRAFORM_DCOS_VERSION_PIN)

    # Our input is assumed in the format.
    # <OS>/<version>/<platform>/<DCOS-version>
    platform = build_dir.split('/')[2]

    cluster_profile = os.path.join(build_dir, CLUSTER_PROFILE_TFVARS)
    with open(cluster_profile, 'a') as f:
        f.write('\n')
        f.write('ssh_user = "{}"'.format(ssh_user))
        f.write('aws_ami = "{}"'.format(ami))

    init_cmd = _tf_init_cmd + platform
    subprocess.run(init_cmd.split(), check=True, cwd=tf_dir)

    return cluster_profile


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

    source_ami_matches = re.search('"source_ami.+', content)
    ami_description_matches = re.search('"ami_description.+', content)

    if not source_ami_matches:
        raise ValueError("source_ami field not found in packer.json")

    base_images_file = _find_files_with_name(os_version_dir, BASE_IMAGES_JSON)

    if base_images_file is None:
        raise ValueError("{file} not found".format(file=BASE_IMAGES_JSON))

    with open(base_images_file) as f:
        ami = json.load(f)[DEFAULT_AWS_REGION]
        content = content.replace(source_ami_matches.group(0), '"source_ami": "{}",'.format(ami))
        # also update the ami description
        content = content.replace(ami_description_matches.group(0), '"ami_description": "{}",'.format(build_dir))

    with open(packer_file, 'w') as f:
        f.write(content)


def _add_private_ips_to_terraform(tf_dir):
    """ Creates an output file for terraform that will supply private ips for cluster agents. This is temporary as it
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


def run_integration_tests(ssh_user, master_public_ips, master_private_ips, private_agent_private_ips,
                          public_agent_private_ips, tf_dir, tests):
    """Run DCOS Integration tests on Terraform cluster.
    """
    env_dict = {'MASTER_HOSTS': '', 'PUBLIC_SLAVE_HOSTS': '', 'SLAVE_HOSTS': ''}

    env_dict['MASTER_HOSTS'] = ','.join(m for m in master_private_ips)
    env_dict['SLAVE_HOSTS'] = ','.join(m for m in private_agent_private_ips)
    env_dict['PUBLIC_SLAVE_HOSTS'] = ','.join(m for m in public_agent_private_ips)

    tests_string = ' '.join(tests)
    env_string = ' '.join(['{}={}'.format(key, env_dict[key]) for key in env_dict.keys()])

    pytest_cmd = """ bash -c "source /opt/mesosphere/environment.export &&
    cd `find /opt/mesosphere/active/ -name dcos-integration-test* | sort | tail -n 1` &&
    {env} py.test -s -vv {tests_list}" """.format(env=env_string, tests_list=tests_string)

    user_and_host = ssh_user + '@' + master_public_ips[0]

    # Running integration tests
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", user_and_host, pytest_cmd], check=True, cwd=tf_dir)


def run_framework_tests(master_public_ip, tf_dir, s3_bucket='osqual-frameworks-artifacts'):
    """ Running data services framework tests - specifically helloworld.
    """
    # Using the sshkey-gpowale branch on the dcos-commons repository for testing.
    subprocess.run('git clone --single-branch -b sshkey-gpowale https://github.com/mesosphere/dcos-commons.git'.split(),
                   check=True, cwd=tf_dir)

    cluster_url = 'https://{}'.format(master_public_ip)

    # Setting environment variables
    new_env = copy.deepcopy(os.environ)
    environment_variables = {
        'CLUSTER_URL': '{}'.format(cluster_url),
        'DCOS_LOGIN_USERNAME': 'bootstrapuser',
        'DCOS_LOGIN_PASSWORD': 'deleteme',
        'S3_BUCKET': '{}'.format(s3_bucket)
    }
    new_env.update(environment_variables)

    # Running helloworld framework tests
    subprocess.run('./{}/dcos-commons/test.sh -o --headless helloworld'.format(tf_dir).split(), env=new_env)


def publish_dcos_images(build_dir):
    """Publish (push) dcos_images.yaml that was generated back to the PR.
    Running this step before integration tests because passing all tests is not necessarily a requirement to qualify and
    publish images, as flakiness and false negatives can happen. The second step is commenting on the PR the link to
    the jenkins build url. This is useful because this new commit will trigger another parallel build and we don't
    want to lose track of the initial one."""
    subprocess.run("""git add dcos_images.yaml packer_build_history.json packer.json &&
                   git commit -m "Publish dcos_images.yaml for {}" &&
                   git push -v""".format(build_dir),
                   check=True, cwd=build_dir, shell=True)

    headers = {
        'Authorization': 'token ' + os.environ['DCOS_IMAGES_PERSONAL_ACCESS_TOKEN'],
        'Accept': 'application/vnd.github.v3+json'
    }
    msg = 'Link to initial jenkins build running cluster creation and integration tests: {}'.format(
        os.environ['JENKINS_BUILD_URL'])
    r = requests.post(
        'https://api.github.com/repos/dcos/dcos-images/issues/{}/comments'.format(os.environ['PULL_REQUEST_ID']),
        data=json.dumps({'body': msg}), headers=headers)
    print('Result of POST request to comment on pr:' + str(r.json()))


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
    valid_keys = [CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, CONFIG_KEY_TESTS_TO_RUN, CONFIG_KEY_RUN_INTEGRATION_TESTS,
                  CONFIG_KEY_RUN_FRAMEWORK_TESTS]

    valid_steps = [PUBLISH_STEP_PACKER_BUILD,
                   PUBLISH_STEP_DCOS_INSTALLATION,
                   PUBLISH_STEP_INTEGRATION_TESTS,
                   PUBLISH_STEP_NEVER]

    _default_publish_dcos_images_after_step = PUBLISH_STEP_DCOS_INSTALLATION

    for k in content:
        if k not in valid_keys:
            raise ValueError("Unrecognized config parameter: {key}".format(key=k))

    for key in CONFIG_KEY_RUN_INTEGRATION_TESTS, CONFIG_KEY_RUN_FRAMEWORK_TESTS:
        if not isinstance(content.get(key, True), bool):
            raise ValueError("Config parameter '{}' value must be a boolean.".format(key))

    if not isinstance(content.get(CONFIG_KEY_TESTS_TO_RUN, []), list):
        raise ValueError("Config parameter '{}' value must be a list.".format(CONFIG_KEY_TESTS_TO_RUN))

    step = content.get(CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, _default_publish_dcos_images_after_step)

    if step not in valid_steps:
        raise ValueError("Invalid value {} for config parameter '{}'. Valid values: {}".format(
            step, CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, valid_steps))


def _get_config_info(build_dir):
    config_path = os.path.join(build_dir, TEST_CONFIG_YAML)

    # No actions to take by default.
    _default_test_list = []
    _default_run_integration_tests = True
    _default_run_framework_tests = True

    if not os.path.exists(config_path):
        return (PUBLISH_STEP_DCOS_INSTALLATION, _default_test_list, _default_run_integration_tests,
                _default_run_framework_tests)

    with open(config_path) as f:
        content = yaml.load(f)
        _validate_config(content)

        return (content.get(CONFIG_KEY_PUBLISH_DCOS_IMAGES_AFTER, PUBLISH_STEP_DCOS_INSTALLATION),
                content.get(CONFIG_KEY_TESTS_TO_RUN, _default_test_list),
                content.get(CONFIG_KEY_RUN_INTEGRATION_TESTS, _default_run_integration_tests),
                content.get(CONFIG_KEY_RUN_FRAMEWORK_TESTS, _default_run_framework_tests))


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


def _get_agent_ips(tf_dir):
    """ Retrieving both the public and private IPs of agents.
    """
    output = subprocess.check_output(['terraform', 'output', '-json'], cwd=tf_dir)
    output_json = json.loads(output.decode("utf-8"))

    master_public_ips = output_json['Master Public IPs']['value']
    master_private_ips = output_json['Master Private IPs']['value']
    private_agent_private_ips = output_json['Private Agent Private IPs']['value']
    public_agent_private_ips = output_json['Public Agent Private IPs']['value']
    return master_public_ips, master_private_ips, private_agent_private_ips, public_agent_private_ips


def setup_terraform(build_dir, tf_dir, ssh_user):
    with open(os.path.join(build_dir, DCOS_IMAGES_YAML)) as f:
        ami = yaml.load(f)[DEFAULT_AWS_REGION]

    cluster_profile = prepare_terraform(build_dir, tf_dir, ami, ssh_user)
    shutil.copyfile(cluster_profile, os.path.join(tf_dir, CLUSTER_PROFILE_TFVARS))
    _add_private_ips_to_terraform(tf_dir)


def setup_cluster_and_test(build_dir, tf_dir, dry_run, tests, publish_step, run_integration, run_framework, ssh_user):
    tf_plan_cmd = 'terraform plan -var-file cluster_profile.tfvars'
    tf_apply_cmd = 'terraform apply -var-file cluster_profile.tfvars -auto-approve'
    tf_destroy_cmd = 'terraform destroy -var-file cluster_profile.tfvars -auto-approve'
    rm_private_ip_file_cmd = "rm private-ip.tf"

    if dry_run:
        subprocess.run(tf_plan_cmd.split(), check=True, cwd=tf_dir)
        return

    try:
        subprocess.run(tf_apply_cmd.split(), check=True, cwd=tf_dir)

        if publish_step == PUBLISH_STEP_DCOS_INSTALLATION:
            publish_dcos_images(build_dir)

        # Retrieving agent IPs.
        master_public_ips, master_private_ips, agent_ips, public_agent_ips = _get_agent_ips(tf_dir)

        # Run Integration Tests.
        integration_tests_failed = False
        if run_integration:
            try:
                run_integration_tests(ssh_user, master_public_ips, master_private_ips, agent_ips, public_agent_ips,
                                      tf_dir, tests)
            except:
                integration_tests_failed = True
                print(traceback.format_exc(limit=5))

        if publish_step == PUBLISH_STEP_INTEGRATION_TESTS:
            publish_dcos_images(build_dir)

        # Run data services framework tests.
        framework_tests_failed = False
        if run_framework:
            try:
                run_framework_tests(master_public_ips[0], tf_dir)
            except:
                framework_tests_failed = True
                print(traceback.format_exc(limit=5))

        exception_message = ''
        if integration_tests_failed:
            exception_message = 'integration tests '
        if framework_tests_failed:
            if exception_message:
                exception_message += 'and '
            exception_message += 'framework tests '
        if exception_message:
            exception_message += 'failed. See error details in the matching test suite logs.'
            raise Exception(exception_message)
    finally:
        # Removing private-ip.tf before destroying cluster.
        subprocess.run(rm_private_ip_file_cmd.split(), check=False, cwd=tf_dir)

        # Whether terraform manages to create the cluster successfully or not, attempt to delete the cluster
        subprocess.run(tf_destroy_cmd.split(), check=True, cwd=tf_dir)


def get_tf_build_dir(build_dir):
    tf_build_dir = os.path.join(build_dir, TEMPDIR_FOR_TF)
    os.mkdir(tf_build_dir)
    return tf_build_dir


def execute_qualification_process(build_dir, dry_run, tests, publish_step, run_integration, run_framework):
    """Execute DC/OS Qualification process.

    :param build_dir: path of the directory that contains all configuration files for the OS to be qualified
    :param tf_dir: directory resulting from terraform init
    :param dry_run: if True, only the code, unit tests and pipeline will be tested. If false, it will build images, spin
        up a cluster and test it (qualification process)
    :param tests: list of tests to run
    :param publish_step: step after which images publishing will be done
    :param run_integration: if True, will run integration tests
    :param run_framework: if True, will run framework tests
    :return:
    """
    packer_validate_and_build(build_dir, dry_run, publish_step)

    tf_build_dir = get_tf_build_dir(build_dir)

    try:
        ssh_user = get_ssh_user_from_packer_json(build_dir)
        setup_terraform(build_dir, tf_build_dir, ssh_user)
        setup_cluster_and_test(build_dir, tf_build_dir, dry_run, tests, publish_step, run_integration, run_framework, ssh_user)
    finally:
        shutil.rmtree(tf_build_dir, ignore_errors=True)


def main(build_dir: str, dry_run: bool, custom_tests: list):
    publish_step, custom_tests_from_config, run_integration, run_framework = _get_config_info(build_dir)
    tests_to_run = custom_tests or custom_tests_from_config
    execute_qualification_process(build_dir, dry_run, tests_to_run, publish_step, run_integration, run_framework)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Build, Test and Qualify DC/OS Image.")

    parser.add_argument(dest="build_dir",
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
