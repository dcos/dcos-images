#!/usr/bin/env groovy
@Library('sec_ci_libs@v2-latest') _
import org.apache.tools.ant.util.*;


node('mesos-ubuntu') {
    checkout scm
    def proc = "/usr/bin/env python3 -c 'streamer.py'".execute()
def b = new StringBuffer()
proc.consumeProcessErrorStream(b)

for (i = 0; i < 100; i++) {
  println proc.text
  println b.toString()
  sleep(1000)
}
}
