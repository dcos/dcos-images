#!/usr/bin/env bash

apt-get install -y curl
curl -L -O https://releases.hashicorp.com/terraform/0.11.7/terraform_0.11.7_linux_amd64.zip
unzip ./terraform*.zip
chmod +x terraform
mv terraform /usr/local/bin
terraform --help
