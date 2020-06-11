// library for managing shared integration like test logic

def build(Map args) {
    def DOCKER_BUILDS = [:]

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        def BUILD_IMAGE = docker.image('ubuntu-19.04:' + args.DOCKER_TAG)
        BUILD_IMAGE.pull()
        // The commands are executed with the 1001:1000 UID:GID (non-root).
        // The download credentials are needed by the image build part
        BUILD_IMAGE.inside('--group-add=docker --ulimit nofile=1024:1024 --env HOME=/home/jenkins -v /var/run/docker.sock:/var/run/docker.sock') {
            versioning = load 'buildscripts/scripts/lib/versioning.groovy'
            def CMK_VERSION = versioning.get_cmk_version(scm, args.VERSION)

            // Initialize our virtual environment before parallelization
            sh("make .venv")

            // Then execute the tests
            try {
                args.DISTRO_LIST.each { DISTRO ->
                    DOCKER_BUILDS[DISTRO] = {
                        stage('test') {
                            dir ('tests-py3') {
                                sh "RESULT_PATH='${WORKSPACE}/test-results/${DISTRO}' EDITION='"+args.EDITION+"' DOCKER_TAG='"+args.DOCKER_TAG+"' VERSION='$CMK_VERSION' DISTRO='$DISTRO' make "+args.MAKE_TARGET
                            }
                        }
                    }
                }
                parallel DOCKER_BUILDS
            } finally {
                stage('archive artifacts') {
                    archiveArtifacts("test-results/**")
                    xunit([Custom(
                        customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                        deleteOutputFiles: true,
                        failIfNotNew: true,
                        pattern: "**/junit.xml",
                        skipNoTestFiles: false,
                        stopProcessingIfError: true
                    )])
                }
            }
        }
    }
}


return this
