#!groovy

/// file: test-integration-single-f12less.groovy

def main() {
    check_job_parameters([
        "EDITION",  // the testees package long edition string (e.g. 'enterprise')
        "DISTRO",   // the testees package distro string (e.g. 'ubuntu-22.04')
        // "DISABLE_CACHE",    // forwarded to package build job (todo)
        // "DOCKER_TAG_BUILD", // test base image tag (todo)
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    //def safe_branch_name = versioning.safe_branch_name(scm);  // todo: this returns rubbish if CUSTOM_GIT_REF is set
    def safe_branch_name = "master";

    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, branch_version, "daily");
    def docker_tag = versioning.select_docker_tag(
            safe_branch_name,  // 'branch'
            "",                // 'build tag'
            "",                // 'folder tag'
    )
    def distro = params.DISTRO;
    if (!distro) {
        raise ("Job parameter DISTRO must be set to nonempty value.");
    }

    def edition = params.EDITION;
    if (!edition) {
        raise ("Job parameter EDITION must be set to nonempty value.");
    }
    def make_target = "test-integration-docker";

    currentBuild.description += (
        """
        |Run integration tests for packages<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |docker_tag: ${docker_tag}<br>
        |edition: ${edition}<br>
        |distro: ${distro}<br>
        |make_target: ${make_target}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...... │${safe_branch_name}│
        |branch_version:........ │${branch_version}│
        |cmk_version:........... │${cmk_version}
        |docker_tag:............ │${docker_tag}│
        |edition:............... │${edition}│
        |distro:................ │${distro}│
        |make_target:........... │${make_target}│
        |===================================================
        """.stripMargin());

    // todo: add upstream project to description
    // todo: add error to description
    // todo: build progress mins?

    stage("Prepare workspace") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            docker_image_from_alias("IMAGE_TESTING").inside(
                "--group-add=${get_docker_group_id()} \
                --ulimit nofile=1024:1024 \
                --env HOME=/home/jenkins \
                ${mount_reference_repo_dir} \
                -v /home/jenkins/.cmk-credentials:/home/jenkins/.cmk-credentials:ro \
                -v /var/run/docker.sock:/var/run/docker.sock") {

                dir("${checkout_dir}") {

                    // Cleanup test results directory before starting the test to prevent previous
                    // runs somehow affecting the current run.
                    sh("rm -rf ${WORKSPACE}/test-results");

                    // Initialize our virtual environment before parallelization
                    sh("make .venv");

                    stage("Fetch Checkmk package") {
                        fetch_job_artifacts(
                            relative_job_name: "builders/build-cmk-distro-package",
                            params: [
                                /// currently CUSTOM_GIT_REF must match, but in the future
                                /// we should define dependency paths for build-cmk-distro-package
                                CUSTOM_GIT_REF: cmd_output("git rev-parse HEAD"),
                                EDITION: edition,
                                DISTRO: distro,
                            ],
                            dest: "package_download",
                        );
                    }
                    try {
                        stage("Run `make ${make_target}`") {
                            dir("${checkout_dir}/tests") { 
                                sh("""
                                    RESULT_PATH='${WORKSPACE}/test-results/${distro}' \
                                    EDITION='${edition}' \
                                    DOCKER_TAG='${docker_tag}' \
                                    VERSION="daily" \
                                    DISTRO='${distro}' \
                                    make ${make_target}
                                """);
                            }
                        }
                    } finally {
                        stage('Archive / process test reports') {
                            dir("${WORKSPACE}") { 
                                archiveArtifacts("test-results/**");

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
                }
            }
        }
    }
}

return this;
