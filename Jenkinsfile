#!/usr/bin/env groovy
@Library('sec_ci_libs@v2-latest') _
import org.apache.tools.ant.util.*;


node('mesos-ubuntu') {
  stage("stream") {
    def proc = "python streamer.py".execute()
    proc.consumeProcessOutput(System.out, System.err)
    println("about to wait")
    proc.waitFor()
    println("noooooooooooooo")
  }
}
