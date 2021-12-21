// library for managing shared integration like test logic

def build(Map args) {
    def DOCKER_BUILDS = [:]

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        def BUILD_IMAGE = docker.build("build-image:${env.BUILD_ID}", "--pull buildscripts/docker_image_aliases/IMAGE_TESTING")
        // The commands are executed with the 1001:1000 UID:GID (non-root).
        // The download credentials are needed by the image build part
        BUILD_IMAGE.inside("--group-add=${args.DOCKER_GROUP_ID} --ulimit nofile=1024:1024 --env HOME=/home/jenkins -v /var/run/docker.sock:/var/run/docker.sock") {
            versioning = load 'buildscripts/scripts/lib/versioning.groovy'
            upload = load 'buildscripts/scripts/lib/upload_artifacts.groovy'
            def CMK_VERSION = versioning.get_cmk_version(scm, args.VERSION)
            def IMAGE_VERSION = args.VERSION == "git" ? versioning.get_date() : CMK_VERSION

            sh("rm -rf \"${WORKSPACE}/packages\"")
            if(args.DISTRO_LIST == ["ubuntu-20.04"]) {
                upload.download_deb(INTERNAL_DEPLOY_DEST, INTERNAL_DEPLOY_PORT, IMAGE_VERSION, "${WORKSPACE}/packages/${IMAGE_VERSION}", args.EDITION, "focal")
            }
            else if(args.DISTRO_LIST.size() == 1) {
                throw new Exception("Please add a case to download only the needed package for ${args.DISTRO_LIST}")
            }
            else {
                upload.download_version_dir(INTERNAL_DEPLOY_DEST, INTERNAL_DEPLOY_PORT, IMAGE_VERSION, "${WORKSPACE}/packages/${IMAGE_VERSION}")
            }

            // Cleanup test results directory before starting the test to prevent previous
            // runs somehow affecting the current run.
            sh("[ -d test-results ] && rm -rf test-results || true")

            // Initialize our virtual environment before parallelization
            sh("make .venv")

            // Then execute the tests
            try {
                args.DISTRO_LIST.each { DISTRO ->
                    DOCKER_BUILDS[DISTRO] = {
                        stage(DISTRO + ' test') {
                            dir ('tests') {
                                sh "RESULT_PATH='${WORKSPACE}/test-results/${DISTRO}' EDITION='"+args.EDITION+"' DOCKER_TAG='"+args.DOCKER_TAG+"' VERSION='$CMK_VERSION' DISTRO='$DISTRO' BRANCH='${args.BRANCH}' make "+args.MAKE_TARGET
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
