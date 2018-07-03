#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

def master_branches = ["master", ] as String[]

// using mesos node because it's a lightweight alpine docker image instead of full VM
node('mesos') {
  stage("Verify author") {
    user_is_authorized(master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify')
  }
}

node('mesos-ubuntu') {
  def shcmd = { String command ->
      output = sh(script: command, returnStdout: true).trim()
      println(output)
      return output
  }

  def paths = []
  checkout scm
  stage("Get changeset") {
    shcmd("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'")
    shcmd('git fetch --all')
    branch = shcmd('git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3')
    shcmd('git checkout master')
    shcmd("git checkout ${branch}")
    shcmd('git config --global user.name "mesosphere_jenkins"')
    shcmd('git config --global user.email "mesosphere_jenkins"')
    shcmd('git rebase master')

    diffOutput = shcmd('git diff --name-only master')
    changedFiles = diffOutput.split('\n')
    for(file in changedFiles) {
      if (file.contains('install_dcos_prerequisites.sh') || file.contains('packer.json')
          || file.contains('build_and_test_dcos_ami.sh')) {
        String path = file.split('/').pop().join('/')
        if (!paths.contains(path)) {
          paths.add(path)
          println("new path ${path}")
        }
      }
    }
  }

  stage("Get packer") {
    shcmd('chmod +x get_packer.sh')
    shcmd('./get_packer.sh')
  }

  stage("Build and test") {
    def builders = [:]
    for (path in paths) {
      println("Building path ${path}")
      builders["build-${item}"] = {
        task_wrapper('mesos-ubuntu', master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify') {
          stage("Build and test") {
            println(sh(script: 'python3 build_test_ami.py ' + path, returnStdout: true).trim())
          }
        }
      }
    }
    parallel builders
  }
}
