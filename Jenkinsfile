#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

def master_branches = ["master", ] as String[]

def builders = [:]

  // using mesos node because it's a lightweight alpine docker image instead of full VM
node('mesos') {
  stage("Verify author") {
    user_is_authorized(master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify')
  }
}

def list = ["A", "B", "C"]
for (item in list) {
  builders["build-${item}"] = {
    task_wrapper('mesos-ubuntu', master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify') {
      stage("Build") {
        checkout scm
        sh 'ci/hello_world.sh'
      }
    }
  }
}

parallel builders