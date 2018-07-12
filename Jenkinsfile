#!/usr/bin/env groovy
import java.lang.*
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
      Process p = command.execute()
      p.consumeProcessOutput(System.out, System.err)
      p.waitForProcessOutput(System.out, System.err)
  }

  checkout scm
  stage("Get changeset") {
    // Jenkins checks out the changes in a detached head state with no concept of what to fetch remotely. So here we
    // change the git config so that fetch will pull all changes from all branches from the remote repository
    shcmd("git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*'")
    shcmd('git fetch --all')
    // Get branch name from checked out commit
    branch = sh(script: 'git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3',
        returnStdout: true).trim()
    println(branch)
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
        def split_list = file.tokenize('/')
        split_list.pop()
        String p = split_list.join('/')
        if (!paths.contains(p)) {
          paths.add(p)
          println("new path ${p}")
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
for (p in paths) {
  println("Building path ${p}")
  builders["build-and-test-${p}"] = {
    task_wrapper('mesos-ubuntu', master_branches, '8b793652-f26a-422f-a9ba-0d1e47eb9d89', '#tools-notify') {
      stage("Build and test") {
        sshagent(['9b6c492f-f2cd-4c79-80dd-beb1238082da']) {
          withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'a20fbd60-2528-4e00-9175-ebe2287906cf', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
            String command = "python3 build_and_test_amis.py ${p}"
            Process ps = command.execute()
            ps.consumeProcessOutput(System.out, System.err)
            ps.waitForProcessOutput(System.out, System.err)
          }
        }
      }
    }
  }
}
parallel builders
