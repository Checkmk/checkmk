properties([
  buildDiscarder(logRotator(artifactDaysToKeepStr: '', artifactNumToKeepStr: '', daysToKeepStr: '7', numToKeepStr: '14')),
])

def NODE = ''
withFolderProperties{
    NODE = env.BUILD_NODE
}

// Due to https://github.com/pypa/pypi-support/issues/978, we need to disable Plugin tests for py2.6
// until we have a feasible solution or we drop the support for 2.6 completly.
def PYTHON_VERSIONS = [ "2.7", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9" ]

timeout(time: 12, unit: 'HOURS') {
    node(NODE) {
        stage('checkout sources') {
            checkout(scm)
        }
        notify = load('buildscripts/scripts/lib/notify.groovy')
        versioning = load('buildscripts/scripts/lib/versioning.groovy')
        docker_util = load ('buildscripts/scripts/lib/docker_util.groovy')
    }

    def DOCKER_BUILDS = [:]

    try {
        node(NODE) {
            docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                def TEST_IMAGE = docker.build("test-image:${env.BUILD_ID}", "--pull buildscripts/docker_image_aliases/IMAGE_TESTING")
                // ID of docker group on the node
                def DOCKER_GROUP_ID = docker_util.get_docker_group_id()
                // The commands are executed with the 1001:1000 UID:GID (non-root).
                // This is the UID of the jenkins user on the node.
                TEST_IMAGE.inside("--ulimit nofile=1024:1024 --group-add=${DOCKER_GROUP_ID} -v /var/run/docker.sock:/var/run/docker.sock") {
                    // pre-create virtual environments before parallel execution
                    stage("prepare virtual environment") {
                        sh("make .venv")
                    }
                    PYTHON_VERSIONS.each { PYTHON_VERSION ->
                        DOCKER_BUILDS[PYTHON_VERSION] = {
                            stage('test agent plugin unit ' + PYTHON_VERSION) {
                                dir('tests') {
                                    sh("bash -c \"make test-agent-plugin-unit-py" + PYTHON_VERSION + "-docker\"")
                                }
                            }
                        }
                    }
                    parallel DOCKER_BUILDS
                }
            }
        }
    } catch(Exception e) {
        notify.notify_error(e)
    }
}
