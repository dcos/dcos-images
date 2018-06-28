apt-get install -y curl
curl -L -O https://releases.hashicorp.com/packer/1.2.4/packer_1.2.4_linux_amd64.zip && unzip ./packer*.zip && chmod +x packer
./packer --help

