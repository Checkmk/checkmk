#!groovy

/// file: test-integration-agent-plugin.groovy

def main() {
    check_job_parameters([
        ["EDITION", true],  // the testees package long edition string (e.g. 'enterprise')
        ["DISTRO", true],  // the testees package distro string (e.g. 'ubuntu-22.04')
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",  // the docker tag to use for building and testing, forwarded to packages build job
        "VERSION",
    ]);

    check_environment_variables([
        "DOCKER_REGISTRY",
        "EDITION",
    ]);

    def single_tests = load("${checkout_dir}/buildscripts/scripts/utils/single_tests.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def version = params.VERSION;
    def distro = params.DISTRO;
    def edition = params.EDITION;

    def make_target = "test-integration-agent-plugin";

    def setup_values = single_tests.common_prepare(version: version, make_target: make_target, docker_tag: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD);

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
        |docker_tag:............ │${setup_values.docker_tag}│
        |===================================================
        """.stripMargin());

    // this is a quick fix for FIPS based tests, see CMK-20851
    def build_node = params.CIPARAM_OVERRIDE_BUILD_NODE;
    if (build_node == "fips") {
        // Do not start builds on FIPS node
        println("Detected build node 'fips', switching this to 'fra'.");
        build_node = "fra"
    }

    dir("${checkout_dir}") {
        inside_container(
            args: [
                "--env HOME=/home/jenkins",
            ],
            set_docker_group_id: true,
            ulimit_nofile: 1024,
            mount_credentials: true,
            privileged: true,
        ) {
            stage("Run `make ${make_target}`") {
                dir("${checkout_dir}/tests") {
                    single_tests.run_make_target(
                        result_path: "${checkout_dir}/test-results",
                        edition: edition,
                        docker_tag: setup_values.docker_tag,
                        version: VERSION == "daily" ? version : cmk_version,
                        distro: distro,
                        branch_name: setup_values.safe_branch_name,
                        make_target: make_target,
                    );
                }
            }
        }
    }
}

return this;
