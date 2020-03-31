#!/bin/bash
vol=$(/usr/sbin/nvme id-ctrl --raw-binary "${1}" | \
      cut -c3073-3104 | tr -s ' ' | sed 's/ $//g')
vol=${vol#/dev/}
[ -n "${vol}" ] && echo "${vol/xvd/sd} ${vol/sd/xvd}"
