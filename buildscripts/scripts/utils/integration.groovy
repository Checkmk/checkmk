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

    def DOCKER_BUILDS = [:];
    def download_dir = "downloaded_packages_for_integration_tests";

    inside_container(
            args: [
                "--ulimit nofile=1024:1024",
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            mount_credentials: true,
            priviliged: true,
    ) {
        // TODO dir + set WORKSPACE is needed due to nested dependency
        dir("${checkout_dir}") {
            withEnv(["WORKSPACE=${WORKSPACE}"]) {
                // TODO or DO NOT REMOVE: this versioning load is needed in order for uplaod_artifacts to have
                // versioning.groovy available.... holy moly
                /* groovylint-disable-next-line UnusedVariable */
                def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
                def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

                // TODO make independent from WORKSPACE
                sh("rm -rf \"${WORKSPACE}/${download_dir}\"")
                if (args.DISTRO_LIST == ["ubuntu-22.04"]) {
                    artifacts_helper.download_deb(
                        INTERNAL_DEPLOY_DEST,
                        INTERNAL_DEPLOY_PORT,
                        args.cmk_version,
                        "${WORKSPACE}/${download_dir}/${args.cmk_version}",
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
                        "${WORKSPACE}/${download_dir}/${args.cmk_version}",
                    );
                }

                // Cleanup test results directory before starting the test to prevent previous
                // runs somehow affecting the current run.
                sh("[ -d ${WORKSPACE}/test-results ] && rm -rf ${WORKSPACE}/test-results || true");

                // Initialize our virtual environment before parallelization
                sh("make .venv");

                // Then execute the tests

                // TODO: We still need here the VERSION/git semantic for the make targets:
                // * case VERSION="2.2.0-2023.06.07" -> use daily build of date as-is
                try {
                    /* groovylint-disable NestedBlockDepth */
                    args.DISTRO_LIST.each { DISTRO ->
                        DOCKER_BUILDS[DISTRO] = {
                            stage(DISTRO + ' test') {
                                dir ('tests') {
                                    sh("""RESULT_PATH='${WORKSPACE}/test-results/${DISTRO}' \
                                    EDITION='${args.EDITION}' \
                                    DOCKER_TAG='${args.DOCKER_TAG}' \
                                    VERSION='${args.VERSION == "daily" ? args.VERSION : args.cmk_version}' \
                                    DISTRO='$DISTRO' \
                                    BRANCH='${args.BRANCH}' \
                                    OTEL_EXPORTER_OTLP_ENDPOINT='${args.OTEL_EXPORTER_OTLP_ENDPOINT}' \
                                    CI_NODE_NAME='${env.NODE_NAME}' \
                                    CI_WORKSPACE='${env.WORKSPACE}' \
                                    CI_JOB_NAME='${env.JOB_NAME}' \
                                    CI_BUILD_NUMBER='${env.BUILD_NUMBER}' \
                                    CI_BUILD_URL='${env.BUILD_URL}' \
                                    make ${args.MAKE_TARGET}""");
                                }
                            }
                        }
                    }
                    /* groovylint-enable NestedBlockDepth */
                    parallel DOCKER_BUILDS;
                } finally {
                    // We sometime see errors during the archive step, like:
                    // ERROR: org.jenkinsci.plugins.compress_artifacts.TrueZipArchiver.visit(TrueZipArchiver.java:77): java.io.FileNotFoundException:
                    // ...test-composition/test-results/ubuntu-24.04/results/comp_0_central/logs/nagios.log (No such file or directory)
                    // Didn't manage to find the issue but we really want to avoid the whole pipline failing bc of that.
                    catchError(buildResult: "SUCCESS", stageResult: "FAILURE") {
                        stage("Archive / process test reports") {
                            dir(WORKSPACE) {
                                show_duration("archiveArtifacts") {
                                    archiveArtifacts(allowEmptyArchive: true, artifacts: "test-results/**");
                                }
                                xunit([Custom(
                                    customXSL: "$JENKINS_HOME/userContent/xunit/JUnit/0.1/pytest-xunit.xsl",
                                    deleteOutputFiles: true,
                                    failIfNotNew: true,
                                    pattern: "**/junit.xml",
                                    skipNoTestFiles: false,
                                    stopProcessingIfError: true
                                )]);
                            }
                        }
                    }
                    /// remove downloaded packages since they consume dozens of GiB
                    sh("""rm -rf "${WORKSPACE}/${download_dir}" """);
                }
            }
        }
    }
}

return this;
