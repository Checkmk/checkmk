#!groovy

// file: assert-release-build-artifacts.groovy

def main() {
    check_job_parameters([
        "VERSION",
    ])

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version_deploy(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |===================================================
        """.stripMargin());

    stage("Assert release build artifacts") {
        docker_image_from_alias("IMAGE_TESTING").inside("-v \$HOME/.cmk-credentials:\$HOME/.cmk-credentials -v /var/run/docker.sock:/var/run/docker.sock --group-add=${get_docker_group_id()}") {
            withEnv(["PYTHONUNBUFFERED=1"]) {
                dir("${checkout_dir}") {
                    sh(script: """scripts/run-pipenv run \
                    buildscripts/scripts/get_distros.py \
                    --editions_file "${checkout_dir}/editions.yml" \
                    assert_build_artifacts \
                    --version "${cmk_version_rc_aware}" \
                    """);
                }
            }
        }
    }
}

return this;
