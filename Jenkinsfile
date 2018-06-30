#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

def master_branches = ["master", ] as String[]

// using mesos node because it's a lightweight alpine docker image instead of full VM
node('mesos') {
  stage("Verify author") {
    user_is_authorized(master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify')
  }
}

def paths = []
node('mesos-ubuntu') {
  stage("Get changeset") {
      def shcmd = { String command ->
        output = sh(script: command, returnStdout: true).trim()
        println(output)
        return output
      }
      checkout scm
      shcmd("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'")
      shcmd('git fetch --all')
      branch = shcmd('git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3')
      shcmd('git checkout origin/' + branch)
      baseCommit = shcmd("git merge-base --fork-point origin/master")
      diffOutput = shcmd("git diff --name-only " + baseCommit)
      changedFiles = diffOutput.split('\n')
      for(file in changedFiles) {
        if (file.contains('install_dcos_prerequisites.sh') || file.contains('packer.json')
            || file.contains('build_and_test_dcos_ami.sh')) {
          String path = file.split('/').pop().join('/')
          if (!paths.contains(path)) {
            paths.add(path)
          }
        }
      }
      shcmd('chmod +x get_packer.sh')
      shcmd('./get_packer.sh')
  }
}

def builders = [:]
for (path in paths) {
  builders["build-${item}"] = {
    task_wrapper('mesos-ubuntu', master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify') {
      stage("Build") {
        String buildScript = path + '/build_and_test_dcos_ami.sh'
        shcmd('chmod +x ' + buildScript)
        shcmd('./' + buildScript)
      }
    }
  }
}

parallel builders
