#!groovy

/// file: test-composition-single-f12less.groovy

def main() {
    check_job_parameters([
        "EDITION",
        "DISTRO",
        "USE_CASE",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    // TODO: we should always use USE_CASE directly from the job parameters
    def use_case = (USE_CASE == "fips") ? USE_CASE : "daily_tests"
    test_jenkins_helper.assert_fips_testing(use_case, NODE_LABELS);
    def distro = params.DISTRO;

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = safe_branch_name;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, "daily");
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        "",                 // 'build tag'
        safe_branch_name,   // 'branch' returns '<BRANCH>-latest'
    );

    def edition = params.EDITION;

    def make_target = "test-composition-docker";

    // Use the directory also used by tests/testlib/containers.py to have it find
    // the downloaded package.
    def download_dir = "package_download";

    currentBuild.description += (
        """
        |Run composition tests for packages<br>
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
        |safe_branch_name:......... │${safe_branch_name}│
        |branch_name:.............. │${branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |edition:.................. │${edition}│
        |distro:................... │${distro}│
        |make_target:.............. │${make_target}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

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
                        build_params_no_check: [
                            CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
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
                                    VERSION='daily' \
                                    DISTRO='${distro}' \
                                    BRANCH='${branch_name}' \
                                    CI_NODE_NAME='${env.NODE_NAME}' \
                                    CI_WORKSPACE='${env.WORKSPACE}' \
                                    CI_JOB_NAME='${env.JOB_NAME}' \
                                    CI_BUILD_NUMBER='${env.BUILD_NUMBER}' \
                                    CI_BUILD_URL='${env.BUILD_URL}' \
                                    make ${make_target}
                                """);
                            }
                        }
                    }
                } finally {
                    stage("Archive / process test reports") {
                        dir("${WORKSPACE}") {
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
            }
        }
    }
}

return this;
