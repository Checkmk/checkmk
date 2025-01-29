#!groovy

/// file: test-schemathesis-openapi-f12less.groovy

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-22.04')
        // "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD", // test base image tag (todo)
        // "DISABLE_CACHE",    // forwarded to package build job (todo)
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, branch_version, "daily");
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch'
    )
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = "test-schemathesis-openapi-docker";
    def download_dir = "package_download";

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
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            priviliged: true,
        ) {
            dir("${checkout_dir}") {
                // Cleanup test results directory before starting the test to prevent previous
                // runs somehow affecting the current run.
                sh("rm -rf ${WORKSPACE}/test-results");

                /// remove downloaded packages since they consume dozens of MiB
                sh("""rm -rf "${checkout_dir}/${download_dir}" """);

                // Initialize our virtual environment before parallelization
                sh("make .venv");

                stage("Fetch Checkmk package") {
                    upstream_build(
                        relative_job_name: "builders/build-cmk-distro-package",
                        build_params: [
                            /// currently CUSTOM_GIT_REF must match, but in the future
                            /// we should define dependency paths for build-cmk-distro-package
                            CUSTOM_GIT_REF: cmd_output("git rev-parse HEAD"),
                            EDITION: edition,
                            DISTRO: distro,
                        ],
                        dest: download_dir,
                    );
                }
                try {
                    stage("Run `make ${make_target}`") {
                        dir("${checkout_dir}/tests") {
                            docker.withRegistry(DOCKER_REGISTRY, "nexus") {
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
                    }
                } finally {
                    stage("Archive / process test reports") {
                        dir("${WORKSPACE}") {
                            show_duration("archiveArtifacts") {
                                archiveArtifacts("test-results/**");
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
            }
        }
    }
}

return this;
