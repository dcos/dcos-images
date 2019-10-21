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
  def jenkins_git_user = "mesosphere_jenkins"
  def branch = ""
  def last_committer = shcmd('git log -1 --pretty=format:\'%an\'')
  if (last_committer == jenkins_git_user) {
    return
  }

  stage("Install python requirements") {
    shcmd("""apt-get -y update &&
          apt-get -y install python3-pip
          pip3 install -r requirements.txt"""
    )
  }

  stage("Run unit tests") {
    sh("python3 -um unittest")
  }

  stage("Set up git repo") {
    // Jenkins checks out the changes in a detached head state with no concept of what to fetch remotely. So here we
    // change the git config so that fetch will pull all changes from all branches from the remote repository
    shcmd("""git config remote.origin.fetch '+refs/heads/*:refs/remotes/origin/*' &&
          git fetch --all"""
    )
    // Get branch name from checked out commit
    branch = shcmd('git ls-remote --heads origin | grep $(git rev-parse HEAD) | cut -d / -f 3')
    shcmd("""git checkout ${branch} &&
          git config --global user.name "${jenkins_git_user}" &&
          git config --global user.email "${jenkins_git_user}" &&
          git merge origin/master"""
    )
  }

  stage("Get changeset") {
    // get changed files from the PR, excluding deleted files
    diffOutput = shcmd('git diff --diff-filter=ACMRTUXB --name-only origin/master')
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

  stage("Get packer") {
    shcmd("""apt-get install -y wget &&
          wget https://releases.hashicorp.com/packer/1.2.4/packer_1.2.4_linux_amd64.zip &&
          unzip ./packer*.zip &&
          chmod +x packer &&
          mv packer /usr/local/bin &&
          packer --help"""
    )
  }

  stage("Get terraform") {
    shcmd("""apt-get install -y wget &&
          wget https://releases.hashicorp.com/terraform/0.11.14/terraform_0.11.14_linux_amd64.zip &&
          unzip ./terraform*.zip &&
          chmod +x terraform &&
          mv terraform /usr/local/bin &&
          terraform --help
          export TF_LOG=DEBUG"""
    )
  }

  stage("Test build_and_test_amis.py (dry run)") {
    sshagent(['9b6c492f-f2cd-4c79-80dd-beb1238082da']) {
      withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'a20fbd60-2528-4e00-9175-ebe2287906cf', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY']]) {
        sh('python3 -u build_test_publish_images.py "oracle-linux/7.4/aws/DCOS-1.11.3/docker-1.13.1" --dry-run')
      }
    }
  }

  stage("Build, test and publish images") {
    sshagent(['9b6c492f-f2cd-4c79-80dd-beb1238082da']) {
      withCredentials([[$class: 'AmazonWebServicesCredentialsBinding', accessKeyVariable: 'AWS_ACCESS_KEY_ID', credentialsId: 'a20fbd60-2528-4e00-9175-ebe2287906cf', secretKeyVariable: 'AWS_SECRET_ACCESS_KEY'],
                       string(credentialsId: 'DCOS_IMAGES_PERSONAL_ACCESS_TOKEN', variable: 'DCOS_IMAGES_PERSONAL_ACCESS_TOKEN')]) {
        // setting up git to be able to push back dcos_images.yaml back to the PR
        shcmd("""git config --global push.default matching &&
              git remote remove origin &&
              git remote add origin https://mesosphere-ci:${DCOS_IMAGES_PERSONAL_ACCESS_TOKEN}@github.com/dcos/dcos-images.git"""
        )
        withEnv(["JENKINS_BUILD_URL=${env.BUILD_URL}",
                 "DCOS_IMAGES_PERSONAL_ACCESS_TOKEN=${DCOS_IMAGES_PERSONAL_ACCESS_TOKEN}",
                 "PULL_REQUEST_ID=${env.CHANGE_ID}"]) {
          for (p in paths) {
            println("Building path ${p}")
            sh("python3 -u build_test_publish_images.py ${p}")
          }
        }
      }
    }
  }
}
