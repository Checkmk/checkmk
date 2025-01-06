#!groovy

/// file: test-integration-agent-plugin.groovy

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def version = params.VERSION;
    def edition = params.EDITION;

    def make_target = "test-integration-agent-plugin-docker";

    currentBuild.description += (
        """
        |Run update tests for packages<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |branch_version: ${branch_version}<br>
        |cmk_version: ${cmk_version}<br>
        |cmk_version_rc_aware: ${cmk_version_rc_aware}<br>
        |edition: ${edition}<br>
        |make_target: ${make_target}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:...... │${safe_branch_name}│
        |branch_version:........ │${branch_version}│
        |cmk_version:........... │${cmk_version}
        |cmk_version_rc_aware:.. │${cmk_version_rc_aware}
        |edition:............... │${edition}│
        |checkout_dir:.......... │${checkout_dir}│
        |make_target:........... │${make_target}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra"
    }

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

                // Initialize our virtual environment before parallelization
                sh("make .venv");

                stage("Run `make ${make_target}`") {
                        dir("${checkout_dir}/tests") {
                            docker.withRegistry(DOCKER_REGISTRY, "nexus") {
                                sh("""
                                    RESULT_PATH='${WORKSPACE}/test-results' \
                                    EDITION='${edition}' \
                                    VERSION='${VERSION == "daily" ? VERSION : cmk_version}' \
                                    BRANCH='${safe_branch_name}' \
                                    make ${make_target}
                                """);
                            }
                        }
                    }
            }
        }
    }
}

return this;
