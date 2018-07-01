#! /usr/bin/env python3

import json
import shlex
import datetime
import logging
from functools import wraps

from subprocess import PIPE, run

import subprocess

import sys

logfile_time = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M")

logging.basicConfig(
        format="%(asctime)s %(message)s",
        filename="log-{timestamp}.log".format(timestamp=logfile_time),
        level=logging.DEBUG)


def log(func):
    @wraps(func)
    def with_logging(*args, **kwargs):
        logging.info("[function] {0}".format(func.__name__))
        return func(*args, **kwargs)
    return with_logging


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
    if (not ignore_failure) and (0 !=process.returncode):
        sys.exit(-1)
    return


def run_captured(cmd: str, ignore_failure=False) -> subprocess.CompletedProcess:
    cmd = shlex.split(cmd)
    process = run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
    print_result(cmd, process)
    if (not ignore_failure) and (0 != process.returncode):
        sys.exit(-1)
    return process


def _packer_validate():
    run_stream("packer validate packer.json")


def _packer_publish():
    run_stream("packer build packer.json")


@log
def publish_packer():
    _packer_validate()
    _packer_publish()


def get_ami_id():
    with open("dcos_cloud_images_ami.json") as fj:
        dcos_cloud_images_dict = json.load(fj)
        last_published = dcos_cloud_images_dict["last_run_uuid"]
        for build in dcos_cloud_images_dict["builds"]:
            if build["packer_run_uuid"] == last_published:
                ami_map = dict(item.split(":") for item in build["artifact_id"].split(","))
                return ami_map["us-west-2"]

@log
def terraform_init():
    run_stream("terraform init -from-module github.com/dcos/terraform-dcos/aws")


def main():
    print(get_ami_id())
    terraform_init()


if __name__ == '__main__':
    main()
