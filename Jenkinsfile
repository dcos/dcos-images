#!/usr/bin/env groovy

@Library('sec_ci_libs@v2-latest') _

def master_branches = ["master", ] as String[]
def paths = []

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

  checkout scm
  stage("Get changeset") {
    // Jenkins checks out the changes in a detached head state with no concept of what to fetch remotely. So here we
    // change the git config so that fetch will pull all changes from all branches from the remote repository
    shcmd("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'")
    shcmd('git fetch --all')
    // Get branch name from checked out commit
    branch = shcmd('git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3')
    shcmd("git checkout ${branch}")
    shcmd('git config --global user.name "mesosphere_jenkins"')
    shcmd('git config --global user.email "mesosphere_jenkins"')
    shcmd('git rebase origin/master')

    // get changed files from the PR
    diffOutput = shcmd('git diff --name-only origin/master')
    changedFiles = diffOutput.split('\n')
    // Create a list of paths to directories than contain changed packer.json or install_dcos_prerequisites.sh
    for(file in changedFiles) {
      println("changed file ${file}")
      if (file.contains('install_dcos_prerequisites.sh') || file.contains('packer.json')) {
        // remove file name, keep only directory name
        def split_list = path.tokenize('/')
        split_list.pop()
        String path = split_list.join('/')
        if (!paths.contains(path)) {
          paths.add(path)
          println("new path ${path}")
        }
      }
    }
  }

  stage("Get packer") {
    shcmd("""apt-get install -y curl &&
          curl -L -O https://releases.hashicorp.com/packer/1.2.4/packer_1.2.4_linux_amd64.zip &&
          unzip ./packer*.zip &&
          chmod +x packer &&
          mv packer /usr/local/bin &&
          packer --help""")
  }

  stage("Get terraform") {
    shcmd("""apt-get install -y curl &&
          curl -L -O https://releases.hashicorp.com/terraform/0.11.7/terraform_0.11.7_linux_amd64.zip &&
          unzip ./terraform*.zip &&
          chmod +x terraform &&
          mv terraform /usr/local/bin &&
          terraform --help""")
  }
}

def builders = [:]
for (path in paths) {
  println("Building path ${path}")
  builders["build-and-test-${path}"] = {
    task_wrapper('mesos-ubuntu', master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify') {
      stage("Build and test") {
        println(sh(script: "python3 build_and_test_amis.py ${path}", returnStdout: true).trim())
      }
    }
  }
}
parallel builders
