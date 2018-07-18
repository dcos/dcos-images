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

  checkout scm
  def paths = []
  
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
    for(changedFile in changedFiles) {
      if (changedFile.contains('install_dcos_prerequisites.sh') || changedFile.contains('packer.json')) {
        println("changed file ${changedFile}")
        // remove changed file's name, keep only directory name
        def split_list = changedFile.tokenize('/')
        split_list.pop()
        String dir = split_list.join('/')
        if (!paths.contains(dir)) {
          paths.add(dir)
          println("new path ${dir}")
        }
      }
    }
  }

  stage("Publish dcos_images.json") {
    sshagent(['mesosphere-ci-github']) {
      shcmd('git config --global push.default simple')
      shcmd('git remote remove origin')
      shcmd('git remote add origin git@github.com:dcos/dcos-images.git')
      shcmd('touch empty_file')
      shcmd('git add empty_file')
      shcmd('git commit -m "test"')
      shcmd('git push')
    }
  }
}
