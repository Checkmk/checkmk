#!groovy

/// file: trigger-fips-chain.groovy

import java.time.LocalDate

void main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters = [
        EDITION: params.EDITION,
        VERSION: params.VERSION,
        OVERRIDE_DISTROS: params.OVERRIDE_DISTROS,
        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
        CUSTOM_GIT_REF: effective_git_ref,

        /// Hardcode the USE_CASE to fips, because this is our only use case here
        USE_CASE: 'fips',
    ];

    def job_parameters_no_check = [
        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |edition:............... │${params.EDITION}│
        |version:............... │${params.VERSION}│
        |safe_branch_name:...... │${safe_branch_name}│
        |override_distros:...... │${params.OVERRIDE_DISTROS}│
        |fake_windows_artifacts: │${params.FAKE_WINDOWS_ARTIFACTS}│
        |custom_git_ref:........ │${effective_git_ref}│
        |safe_branch_name:...... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    def success = true;

    // We currently run those tests sequential due to resource constraints.
    // use smart_stage to capture build result, but continue with next steps
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        success &= smart_stage(
                name: "Run composition tests on FIPS",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/fips/test-composition-fips",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        success &= smart_stage(
                name: "Run GUI End-to-End tests on FIPS",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/fips/test-gui-e2e-fips",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        success &= smart_stage(
                name: "Run integration tests on FIPS",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/fips/test-integration-fips",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        currentBuild.result = success ? "SUCCESS" : "FAILURE";
    }
}

return this;
