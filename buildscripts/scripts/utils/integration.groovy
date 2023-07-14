#!groovy

/// file: integration.groovy

// library for managing shared integration like test logic

def run_make_targets(Map args) {
    println("""
        ||== RUN INTEGRATION TEST ==============================================
        ||EDITION = ${args.EDITION}
        ||VERSION = ${args.VERSION}
        ||DOCKER_TAG = ${args.DOCKER_TAG}
        ||cmk_version = ${args.cmk_version}
        ||BRANCH = ${args.BRANCH}
        ||MAKE_TARGET = ${args.MAKE_TARGET}
        ||DOCKER_GROUP_ID = ${args.DOCKER_GROUP_ID}
        ||DISTRO_LIST = ${args.DISTRO_LIST}
        ||======================================================================
        """.stripMargin());

    def DOCKER_BUILDS = [:]

    // TODO: this should be done by the top level scripts
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(
            "--group-add=${args.DOCKER_GROUP_ID} \
            --ulimit nofile=1024:1024 \
            --env HOME=/home/jenkins \
            ${mount_reference_repo_dir} \
            -v /home/jenkins/.cmk-credentials:/home/jenkins/.cmk-credentials:ro \
            -v /var/run/docker.sock:/var/run/docker.sock") {

            // TODO dir + set WORKSPACE is needed due to nested dependency
            dir("${checkout_dir}") {
                withEnv(["WORKSPACE=${WORKSPACE}"]) {

                    // TODO or DO NOT REMOVE: this versioning load is needed in order for uplaod_artifacts to have
                    // versioning.groovy available.... holy moly
                    def versioning = load "${checkout_dir}/buildscripts/scripts/utils/versioning.groovy"
                    def artifacts_helper = load "${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy"

                    // TODO make independent from WORKSPACE
                    sh("rm -rf \"${WORKSPACE}/packages\"")
                    if (args.DISTRO_LIST == ["ubuntu-20.04"]) {
                        artifacts_helper.download_deb(
                            INTERNAL_DEPLOY_DEST,
                            INTERNAL_DEPLOY_PORT,
                            args.cmk_version,
                            "${WORKSPACE}/packages/${args.cmk_version}",
                            args.EDITION,
                            "focal",
                        );
                    }
                    else if (args.DISTRO_LIST == ["ubuntu-22.04"]) { // needed for saas nightly int tests
                        artifacts_helper.download_deb(
                            INTERNAL_DEPLOY_DEST,
                            INTERNAL_DEPLOY_PORT,
                            args.cmk_version,
                            "${WORKSPACE}/packages/${args.cmk_version}",
                            args.EDITION,
                            "jammy",
                        );
                    }
                    else if(args.DISTRO_LIST.size() == 1) {
                        raise("Please add a case to download only the needed package for ${args.DISTRO_LIST}");
                    }
                    else {
                        artifacts_helper.download_version_dir(
                            INTERNAL_DEPLOY_DEST,
                            INTERNAL_DEPLOY_PORT,
                            args.cmk_version,
                            "${WORKSPACE}/packages/${args.cmk_version}",
                        );
                    }

                    // Cleanup test results directory before starting the test to prevent previous
                    // runs somehow affecting the current run.
                    sh("[ -d ${WORKSPACE}/test-results ] && rm -rf ${WORKSPACE}/test-results || true")

                    // Initialize our virtual environment before parallelization
                    sh("make .venv")

                    // Then execute the tests

                    // TODO: We still need here the VERSION/git semantic for the make targets:
                    // * case VERSION="git" -> use daily build but patch it using f12
                    // * case VERSION="2.2.0-2023.06.07" -> use daily build of date as-is
                    try {
                        args.DISTRO_LIST.each { DISTRO ->
                            DOCKER_BUILDS[DISTRO] = {
                                stage(DISTRO + ' test') {
                                    dir ('tests') {
                                        sh("""RESULT_PATH='${WORKSPACE}/test-results/${DISTRO}' \
                                        EDITION='${args.EDITION}' \
                                        DOCKER_TAG='${args.DOCKER_TAG}' \
                                        VERSION='${args.VERSION in ["git", "daily"] ? args.VERSION : args.cmk_version}' \
                                        DISTRO='$DISTRO' \
                                        BRANCH='${args.BRANCH}' \
                                        make ${args.MAKE_TARGET}""");
                                    }
                                }
                            }
                        }
                        parallel DOCKER_BUILDS
                    } finally {
                        stage('archive artifacts') {
                            dir(WORKSPACE) {
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
        }
    }
}
return this;
