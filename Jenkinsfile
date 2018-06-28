#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

def master_branches = ["master", ] as String[]

ansiColor('xterm') {
  // using mesos node because it's a lightweight alpine docker image instead of full VM
  node('mesos-ubuntu') {
    stage("Verify author") {
      user_is_authorized(master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify')
    }

    stage("a hello world") {
      checkout scm
      sh 'chmod +x ci_test_script.sh'
      sh './ci_test_script.sh'
    }
  }
}
