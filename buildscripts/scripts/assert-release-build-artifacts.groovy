#!groovy

// file: assert-release-build-artifacts.groovy

def main() {
    check_job_parameters([
        "VERSION",
        "USE_CASE"
    ])

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def use_case = params.USE_CASE.trim() ?: "daily";

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
        inside_container(
            set_docker_group_id: true,
            mount_credentials: true,
            priviliged: true,
        ) {
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USER')]) {
                withEnv(["PYTHONUNBUFFERED=1"]) {
                    dir("${checkout_dir}") {
                        sh(script: """scripts/run-pipenv run \
                        buildscripts/scripts/assert_build_artifacts.py \
                        --editions_file "${checkout_dir}/editions.yml" \
                        assert_build_artifacts \
                        --version "${cmk_version_rc_aware}" \
                        --use_case "${use_case}"
                        """);
                    }
                }
            }
        }
    }
}

return this;
