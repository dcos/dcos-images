#!/usr/bin/env groovy


node('mesos-ubuntu') {
    checkout scm
    sh("python3 streamer.py")
}
