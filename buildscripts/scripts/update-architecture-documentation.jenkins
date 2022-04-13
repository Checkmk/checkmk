def NODE = "linux"

properties([
    buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
    pipelineTriggers([pollSCM('H/2 * * * *')]),
])
ansiColor("xterm"){
    timeout(time: 12, unit: 'HOURS') {
        node (NODE) {
            stage('checkout sources') {
                checkout(scm)
                notify = load 'buildscripts/scripts/lib/notify.groovy'
            }
            try {
                stage("Update") {
                    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                        def BUILD_IMAGE = docker.build("build-image:${env.BUILD_ID}", "--pull ${WORKSPACE}/buildscripts/docker_image_aliases/IMAGE_TESTING")
                        BUILD_IMAGE.inside() {
                            sh("make -C doc/documentation htmlhelp")
                        }
                    }
                }
                stage("Stash") {
                    stash(
                        name: "htmlhelp",
                        includes: "doc/documentation/_build/htmlhelp/**"
                    )
                }
            } catch(Exception e) {
                notify.notify_error(e)
            }
        }

        // The pages produced by the job are served by the web server on our CI
        // master node. Extract the results there to make it available to the
        // web server.
        node("Master_DoNotUse") {
            unstash("htmlhelp")
        }
    }
}

