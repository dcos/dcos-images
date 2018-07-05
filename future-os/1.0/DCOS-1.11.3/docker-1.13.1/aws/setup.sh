#!/usr/bin/env bash
echo -e "\nnameserver 8.8.8.8" >> /etc/resolv.conf
systemctl restart network
