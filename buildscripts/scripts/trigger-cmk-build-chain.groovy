#!groovy

/// file: trigger-cmk-build-chain.groovy

import java.time.LocalDate

def main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_REMOVE_RC_CANDIDATES",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
        "SET_LATEST_TAG",
        "SET_BRANCH_LATEST_TAG",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def edition = JOB_BASE_NAME.split("-")[-1];
    def edition_base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/nightly-${edition}";

    def use_case = LocalDate.now().getDayOfWeek().toString() in ["SATURDAY", "SUNDAY"] ? "weekly" : "daily";
    def safe_branch_name = versioning.safe_branch_name();

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters_common = [
        // FIXME: all parameters from all triggered jobs have to be handled here
        EDITION: edition,
        VERSION: params.VERSION,
        OVERRIDE_DISTROS: params.OVERRIDE_DISTROS,
        CIPARAM_REMOVE_RC_CANDIDATES: params.CIPARAM_REMOVE_RC_CANDIDATES,
        FAKE_WINDOWS_ARTIFACTS: params.FAKE_WINDOWS_ARTIFACTS,
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
        SET_LATEST_TAG: params.SET_LATEST_TAG,
        SET_BRANCH_LATEST_TAG: params.SET_BRANCH_LATEST_TAG,
        PUSH_TO_REGISTRY: params.PUSH_TO_REGISTRY,
        PUSH_TO_REGISTRY_ONLY: params.PUSH_TO_REGISTRY_ONLY,
        BUILD_CLOUD_IMAGES: true,
        CUSTOM_GIT_REF: params.CUSTOM_GIT_REF ?: effective_git_ref,
        // PUBLISH_IN_MARKETPLACE will only be set during the release process (aka bw-release)
        PUBLISH_IN_MARKETPLACE: false,
    ];

    def job_parameters_use_case = [
        USE_CASE: use_case,
    ];

    def job_parameters_no_check = [
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
    ];

    job_parameters = job_parameters_common + job_parameters_use_case;

    // TODO we should take this list from a single source of truth
    assert edition in ["cloud", "enterprise", "managed", "raw", "saas"] : (
        "Do not know edition '${edition}' extracted from ${JOB_BASE_NAME}");

    def build_image = true;
    def run_int_tests = true;
    def run_fips_tests = edition == "enterprise";
    def run_comp_tests = !(edition in ["saas"]);
    def run_image_tests = !(edition in ["saas", "managed"]);
    def run_update_tests = (edition in ["cloud", "enterprise", "managed", "raw", "saas"]);

    print(
        """
        |===== CONFIGURATION ===============================
        |edition:............... │${edition}│
        |edition_base_folder:... │${edition_base_folder}│
        |build_image:........... │${build_image}│
        |run_comp_tests:........ │${run_comp_tests}│
        |run_int_tests:......... │${run_int_tests}│
        |run_fips_tests:........ │${run_fips_tests}│
        |run_image_tests:....... │${run_image_tests}│
        |run_update_tests:...... │${run_update_tests}│
        |use_case:.............. │${use_case}│
        |safe_branch_name:...... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    def success = true;

    // use smart_stage to capture build result, but continue with next steps
    // this runs the consecutive stages and jobs in any case which makes it easier to re-run or fix only those distros with the next run
    // which actually failed without triggering all jobs for all but the failing distros
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        success &= smart_stage(
                name: "Build Packages",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${edition_base_folder}/build-cmk-deliverables",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        success &= smart_stage(
                name: "Build CMK IMAGE",
                condition: build_image,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${edition_base_folder}/build-cmk-image",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        /// Run system tests in parallel.
        parallel([
            "Integration Test for Docker Container": {
                success &= smart_stage(
                        name: "Integration Test for Docker Container",
                        condition: run_image_tests,
                        raiseOnError: false,) {
                    smart_build(
                        use_upstream_build: true,
                        relative_job_name: "${edition_base_folder}/test-integration-docker",
                        build_params: job_parameters,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "Integration Test for Packages": {
                success &= smart_stage(
                        name: "Integration Test for Packages",
                        condition: run_int_tests,
                        raiseOnError: false,) {
                    smart_build(
                        use_upstream_build: true,
                        relative_job_name: "${edition_base_folder}/test-integration-packages",
                        build_params: job_parameters,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "Composition Test for Packages": {
                success &= smart_stage(
                        name: "Composition Test for Packages",
                        condition: run_comp_tests,
                        raiseOnError: false,) {
                    smart_build(
                        use_upstream_build: true,
                        relative_job_name: "${edition_base_folder}/test-composition",
                        build_params: job_parameters,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
            "Update Test": {
                success &= smart_stage(
                        name: "Update Test",
                        condition: run_update_tests,
                        raiseOnError: false,) {
                    smart_build(
                        use_upstream_build: true,
                        relative_job_name: "${edition_base_folder}/test-update",
                        build_params: job_parameters,
                        build_params_no_check: job_parameters_no_check,
                        download: false,
                    );
                }[0]
            },
        ]);

        success &= smart_stage(
                name: "Build Packages again",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${edition_base_folder}/build-cmk-deliverables",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        success &= smart_stage(
                name: "Trigger SaaS Gitlab jobs",
                condition: false,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${edition_base_folder}/trigger-saas-gitlab",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }[0]

        currentBuild.result = success ? "SUCCESS" : "FAILURE";
    }
}

return this;
