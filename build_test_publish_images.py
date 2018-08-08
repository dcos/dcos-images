#!/usr/bin/env python3
import argparse
import copy
import json
import os
import pexpect
import re
import requests
import shutil
import stat
import subprocess
import yaml
import requests

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


def update_source_image(build_dir):
    os_version_dir = '/'.join(build_dir.split('/')[:2])
    packer_file = os.path.join(build_dir, 'packer.json')
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


def add_private_ips_to_terraform(tf_dir):
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


def get_agent_ips():
    """ Retrieving both the public and private IPs of agents.
    """
    output = subprocess.check_output(['terraform', 'output', '-json'], cwd=tf_dir)
    output_json = json.loads(output.decode("utf-8"))

    master_public_ips = output_json['Master Public IPs']['value']
    master_private_ips = output_json['Master Private IPs']['value']
    private_agent_private_ips = output_json['Private Agent Private IPs']['value']
    public_agent_private_ips = output_json['Public Agent Private IPs']['value']
    return master_public_ips, master_private_ips, private_agent_private_ips, public_agent_private_ips


def run_integration_tests(ssh_user, master_public_ips, master_private_ips, private_agent_private_ips, public_agent_private_ips, tf_dir, tests):
    """ Running dcos integration tests on terraform cluster.
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
    subprocess.run(["ssh", "-o", "StrictHostKeyChecking=no", user_and_host, pytest_cmd], check=False, cwd=tf_dir)


def download_cli(tf_dir, cli_version='dcos-1.12'):
    """ Installing DC/OS CLI based on the version of DC/OS that is being tested to run framework tests.
    """
    download_url = 'https://downloads.dcos.io/binaries/cli/linux/x86-64/{}/dcos'.format(cli_version)
    download_path = os.path.join(tf_dir, "dcos")
    with open(download_path, 'wb') as f:
        r = requests.get(download_url, stream=True, verify=True)
        for chunk in r.iter_content(8192):
            f.write(chunk)

    # Making binary executable.
    st = os.stat(download_path)
    os.chmod(download_path, st.st_mode | stat.S_IEXEC)


def authenticate(tf_dir, master_public_ip):
    """ Setting up and authenticating into Open DC/OS cluster.
    """
    auth_token = 'eyJ0eXAiOiJKV1QiLCJhbGciOiJSUzI1NiIsImtpZCI6Ik9UQkVOakZFTWtWQ09VRTRPRVpGTlRNMFJrWXlRa015Tnprd1JrSkVRemRCTWpBM1FqYzVOZyJ9.eyJlbWFpbCI6ImFsYmVydEBiZWtzdGlsLm5ldCIsImVtYWlsX3ZlcmlmaWVkIjp0cnVlLCJpc3MiOiJodHRwczovL2Rjb3MuYXV0aDAuY29tLyIsInN1YiI6Imdvb2dsZS1vYXV0aDJ8MTA5OTY0NDk5MDExMTA4OTA1MDUwIiwiYXVkIjoiM3lGNVRPU3pkbEk0NVExeHNweHplb0dCZTlmTnhtOW0iLCJleHAiOjIwOTA4ODQ5NzQsImlhdCI6MTQ2MDE2NDk3NH0.OxcoJJp06L1z2_41_p65FriEGkPzwFB_0pA9ULCvwvzJ8pJXw9hLbmsx-23aY2f-ydwJ7LSibL9i5NbQSR2riJWTcW4N7tLLCCMeFXKEK4hErN2hyxz71Fl765EjQSO5KD1A-HsOPr3ZZPoGTBjE0-EFtmXkSlHb1T2zd0Z8T5Z2-q96WkFoT6PiEdbrDA-e47LKtRmqsddnPZnp0xmMQdTr2MjpVgvqG7TlRvxDcYc-62rkwQXDNSWsW61FcKfQ-TRIZSf2GS9F9esDF4b5tRtrXcBNaorYa9ql0XAWH5W_ct4ylRNl3vwkYKWa4cmPvOqT5Wlj9Tf0af4lNO40PQ'

    child = pexpect.spawn('dcos cluster setup {}'.format(master_public_ip), cwd=tf_dir)
    child.expect('Enter OpenID Connect ID Token:')
    child.sendline(auth_token)
    child.expect(pexpect.EOF, timeout=None)


def run_framework_tests(dcos_major_version, master_public_ip, tf_dir, s3_bucket='infinity-artifacts'):
    """ Running data services framework tests - specifically helloworld.
    """
    subprocess.run('git clone --single-branch -b sshkey-gpowale https://github.com/mesosphere/dcos-commons.git'.split(), check=True, cwd=tf_dir)
    # download_cli(tf_dir) if dcos_major_version == 'master' else download_cli(tf_dir, 'dcos-{}'.format(dcos_major_version))
    
    # authenticate(tf_dir, master_public_ip)
    cluster_url = 'https://{}'.format(master_public_ip)

    # Setting environment variables
    new_env = copy.deepcopy(os.environ)
    new_env.update({'CLUSTER_URL': '{}'.format(cluster_url), 'DCOS_LOGIN_USERNAME': 'bootstrapuser', 'DCOS_LOGIN_PASSWORD': 'deleteme', 'STUB_UNIVERSE_URL': 'https://infinity-artifacts-ci.s3.amazonaws.com/autodelete7d/hello-world/20180808-102039-zQ7fJO5vUHNA21pE/stub-universe-hello-world.json', 'S3_BUCKET': '{}'.format(s3_bucket)})

    # Running helloworld framework tests
    subprocess.run('./{}/dcos-commons/test.sh -o helloworld'.format(tf_dir).split(), env=new_env)


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
    with open(os.path.join(build_dir, 'packer_build_history.json')) as f:
        content = json.load(f)
    builds = content['builds'][-1]['artifact_id'].split(',')
    builds = {build.split(':')[0]: build.split(':')[1] for build in builds}
    with open(os.path.join(build_dir, 'dcos_images.yaml'), 'w') as f:
        f.write(yaml.dump(builds, default_flow_style=False))


def main(build_dir, tf_dir, dry_run, tests, publish_step):
    vars_string, platform, cluster_profile, os_name, ssh_user = prepare_terraform(build_dir, tf_dir)
    update_source_image(build_dir)
    subprocess.run('packer validate packer.json'.split(), check=True, cwd=build_dir)
    if not dry_run and publish_step != 'never':
        subprocess.run('packer build packer.json'.split(), check=True, cwd=build_dir)
        extract_dcos_images(build_dir)
        if publish_step == 'packer_build':
            publish_dcos_images(build_dir)
    with open(os.path.join(build_dir, 'dcos_images.yaml')) as f:
        ami = yaml.load(f)['us-west-2']
    terraform_add_os(build_dir, tf_dir, platform, vars_string, ami, os_name)
    shutil.copyfile(cluster_profile, os.path.join(tf_dir, 'desired_cluster_profile.tfvars'))
    dcos_version = build_dir.split('/')[3].split('-')[1]
    dcos_major_version = dcos_version[0:4] if not dcos_version.isalpha() else 'master'
    url = "https://downloads.dcos.io/dcos/{}/dcos_generate_config.sh"
    dcos_download_url = url.format('stable/' + dcos_version) if not dcos_version.isalpha() else url.format('testing/' + dcos_version)
    with open(os.path.join(tf_dir, 'desired_cluster_profile.tfvars'), "a") as f:
       f.write('\ndcos_version = "{}"\n'.format(dcos_version))
       f.write('custom_dcos_download_path = "{}"\n'.format(dcos_download_url))
    # Getting private IPs of all cluster agents.
    add_private_ips_to_terraform(tf_dir)
    if dry_run:
        subprocess.run('terraform plan -var-file desired_cluster_profile.tfvars'.split(), check=True, cwd=tf_dir)
    else:
        try:
            # Create terraform cluster
            subprocess.run('terraform apply -var-file desired_cluster_profile.tfvars -auto-approve'.split(), check=True,
                           cwd=tf_dir)
            if publish_step == 'dcos_installation':
                publish_dcos_images(build_dir)
            # Retrieving agent IPs.
            master_public_ips, master_private_ips, agent_ips, public_agent_ips = get_agent_ips()
            # Run DC/OS integration tests.
            run_integration_tests(ssh_user, master_public_ips, master_private_ips, agent_ips, public_agent_ips, tf_dir, tests)
            if publish_step == 'integration_tests':
                publish_dcos_images(build_dir)
            # Run data services framework tests.
            run_framework_tests(dcos_major_version, master_public_ips[0], tf_dir)
        finally:
            # Removing private-ip.tf before destroying cluster.
            subprocess.run(["rm", "private-ip.tf"], check=True, cwd=tf_dir)
            # Whether terraform manages to create the cluster successfully or not, attempt to delete the cluster
            subprocess.run('terraform destroy -var-file desired_cluster_profile.tfvars -auto-approve'.split(),
                           check=True, cwd=tf_dir)


def validate_config(content):
    valid_steps = ['packer_build', 'dcos_installation', 'integration_tests', 'never']
    valid_keys = ['publish_dcos_images_after', 'tests_to_run']
    for k in content:
        if k not in valid_keys:
            raise Exception('Unrecognized config parameter ' + k)
    if not isinstance(content.get('tests_to_run', []), list):
        raise Exception("config parameter 'tests_to_run' value must be a list")
    step = content.get('publish_dcos_images_after', 'dcos_installation')
    if step not in valid_steps:
        raise Exception("Invalid value {} for config parameter 'publish_dcos_images_after'. Valid values: {}".
                        format(step, valid_steps))


def get_config_info(build_dir):
    config_path = os.path.join(build_dir, 'publish_and_test_config.yaml')
    if not os.path.exists(config_path):
        return 'dcos_installation', []
    with open(config_path, 'r') as f:
        content = yaml.load(f)
        validate_config(content)
        content.setdefault('publish_dcos_images_after', 'dcos_installation')
        content.setdefault('tests_to_run', [])
        return content['publish_dcos_images_after'], content['tests_to_run']


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Builds and tests DC/OS images')
    parser.add_argument('build_dir', help='The directory that contains all the files necessary to build a dcos image '
                                          'using packer and launch a terraform cluster.')
    parser.add_argument('--dry-run', action='store_true', dest='dry_run', default=False,
                        help='Specifying this flag will run the script without: running the packer build, creating a '
                             'terraform cluster and running the integration tests. It will still run "packer validate" '
                             'and "terraform plan".')
    parser.add_argument('-k', dest='custom_tests', default=None, nargs='*', help='Run specific integration tests.')
    args = parser.parse_args()
    publish_step, custom_tests = get_config_info(args.build_dir)
    tests = args.custom_tests if args.custom_tests is not None else custom_tests
    tf_dir = os.path.join(args.build_dir, 'temp')
    os.mkdir(tf_dir)
    try:
        main(args.build_dir, tf_dir, args.dry_run, tests, publish_step)
    finally:
        # whatever happens we want to make sure the terraform directory is deleted. This is convenient for local testing
        if os.path.exists(tf_dir):
            shutil.rmtree(tf_dir, ignore_errors=True)
