#!/usr/bin/env bash

set -o errexit -o nounset -o pipefail

function globals {
    export LC_ALL=en_US.UTF-8
    export LANG="$LC_ALL"
}; globals

PROJECT_BASE_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )"/.. && pwd )"

function now { date +"%Y-%m-%dT%H:%M:%S.000" | tr -d '\n' ;}
function println { printf '%s\n' "$(now) $*" ;}
function msg { println "$*" >&2 ;}
function err { local x=$? ; msg "$*" ; return $(( x == 0 ? 1 : x )) ;}


function publish_packer {
    msg "packer publishing start"
    packer validate packer.json
    packer build packer.json
}

function get_ami_id {
    msg "gets the ami id from the packer build"
    ami_id=$(cat dcos_cloud_images_ami.json | jq '.'builds[-1].artifact_id | gawk -v RS='[,"]' -F: '$1 == "us-west-2" {print $2}')
    echo ami_id
}

function use_ami_with_terraform {
    msg "uses the ami with the terraform installer and sets up the dcos cluster."
    ami_id_to_use=$(get_ami_id)
    echo ami_id_to_use
}

function run_dcos_integration_test {
    msg "exercises dcos integration test."
}

function main {
    msg "running build for oracle linux (get it from env)."
    publish_packer
    use_ami_with_terraform
    run_dcos_integration_test
}

######################### Delegates to subcommands or runs main, as appropriate
if [[ ${1:-} ]] && declare -F | cut -d' ' -f3 | grep -Fqx -- "${1:-}"
then "$@"
else main
fi
