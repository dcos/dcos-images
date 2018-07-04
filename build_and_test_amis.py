#! /usr/bin/env python3

import datetime
import os
import contextlib
import json
import shlex
import logging
import subprocess
import sys

from functools import wraps


logfile_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")

logging.basicConfig(
        format="%(asctime)s %(message)s",
        filename="log-{timestamp}.log".format(timestamp=logfile_time),
        level=logging.DEBUG)


def fail(msg):
    print(msg)
    sys.exit(-1)


def log(func):
    @wraps(func)
    def with_logging(*args, **kwargs):
        logging.info("[function] {0}".format(func.__name__))
        return func(*args, **kwargs)
    return with_logging


@contextlib.contextmanager
def pushd(dir):
    cwd = os.getcwd()
    try:
        path = os.path.abspath(dir)
        os.chdir(path)
        yield
    except OSError:
        pass
    finally:
        os.chdir(cwd)


def print_result(cmd, result: subprocess.CompletedProcess):
    print("Failed: '{command}' [retcode: {retcode}].".format(command=cmd, retcode=result.returncode))
    print("STDOUT:\n{stdout}\nSTDERR:\n{stderr}".format(stdout=result.stdout, stderr=result.stderr))


def run_stream(cmd: str, ignore_failure=False) -> None:
    cmd = shlex.split(cmd)
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    while True:
        out = process.stdout.read(1)
        if out == b'' and process.poll() is not None:
            break
        if out != b'':
            sys.stdout.write(out.decode("utf-8"))
        sys.stdout.flush()
    err = process.stderr.read()
    sys.stderr.write(err.decode("utf-8"))
    if (not ignore_failure) and (0 !=process.returncode):
        sys.exit(-1)
    return


def run_captured(cmd: str, ignore_failure=False) -> subprocess.CompletedProcess:
    cmd = shlex.split(cmd)
    process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    print_result(cmd, process)
    if (not ignore_failure) and (0 != process.returncode):
        sys.exit(-1)
    return process


def execute_with_dir_context_with_progress(dir, cmd):
    logging.debug("[command] {cmd}".format(cmd=cmd))
    if not os.path.exists(dir):
        fail("{dir} does not exists.".format(dir=dir))
    with pushd(dir):
        run_stream(cmd)


def _packer_validate(dirname):
    execute_with_dir_context_with_progress(dirname, "packer validate packer.json")


def _packer_publish(dirname):
    execute_with_dir_context_with_progress(dirname, "packer build packer.json")


@log
def publish_packer(dirname):
    _packer_validate(dirname)
    _packer_publish(dirname)


def get_ami_id(dirname):
    with pushd(dirname):
        with open("dcos_images.json") as fj:
            dcos_cloud_images_dict = json.load(fj)
            last_published = dcos_cloud_images_dict["last_run_uuid"]
            for build in dcos_cloud_images_dict["builds"]:
                if build["packer_run_uuid"] == last_published:
                    ami_map = dict(item.split(":") for item in build["artifact_id"].split(","))
                    return ami_map["us-west-2"]

@log
def terraform_init(dirname):
    execute_with_dir_context_with_progress(dirname, "terraform init -from-module github.com/dcos/terraform-dcos/aws")

@log
def terraform_add_os(dirname):
    execute_with_dir_context_with_progress(dirname, "cp ../variables.tf modules/dcos-tested-aws-oses/")
    execute_with_dir_context_with_progress(dirname, "mkdir -p modules/dcos-tested-aws-oses/platform/cloud/aws/oracle")
    execute_with_dir_context_with_progress(dirname, "cp ../setup.sh modules/dcos-tested-aws-oses/platform/cloud/aws/oracle")

@log
def terraform_copy_desired_cluster_profile(dirname):
    execute_with_dir_context_with_progress(dirname, "cp ../desired_cluster_profile.tfvars desired_cluster_profile.tfvars")

@log
def terraform_apply(dirname):
    execute_with_dir_context_with_progress(dirname, "terraform apply -var-file desired_cluster_profile.tfvars --auto-approve")


def main():
    if len(sys.argv) != 2:
        print("Usage: ./build_and_test_amis.py os-support-dir.")
        print("Please refer to README the expected files in the support-dir.")
        sys.exit(1)
    dirname = sys.argv[1]
    publish_packer(dirname)
    ami_id = get_ami_id(dirname)
    os.mkdir(ami_id)
    terraform_init(ami_id)
    terraform_add_os(ami_id)
    terraform_copy_desired_cluster_profile(ami_id)
    terraform_apply(ami_id)


if __name__ == '__main__':
    main()
