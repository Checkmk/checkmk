#!groovy

/// file: trigger-cmk-build-chain.groovy

/// This job will trigger other jobs

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

    def edition = JOB_BASE_NAME.split("-")[-1];
    def edition_base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/nightly-${edition}";

    def use_case = LocalDate.now().getDayOfWeek() in ["SATURDAY", "SUNDAY"] ? "weekly" : "daily";

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters_common = [
        stringParam(name: 'EDITION', value: edition),

        // TODO perhaps use `params` + [EDITION]?
        // FIXME: all parameters from all triggered jobs have to be handled here
        stringParam(name: 'VERSION', value: VERSION),
        stringParam(name: 'OVERRIDE_DISTROS', value: params.OVERRIDE_DISTROS),
        booleanParam(name: 'CIPARAM_REMOVE_RC_CANDIDATES', value: params.CIPARAM_REMOVE_RC_CANDIDATES),
        booleanParam(name: 'FAKE_WINDOWS_ARTIFACTS', value: params.FAKE_WINDOWS_ARTIFACTS),
        stringParam(name: 'CIPARAM_OVERRIDE_DOCKER_TAG_BUILD', value: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD),
        booleanParam(name: 'SET_LATEST_TAG', value: params.SET_LATEST_TAG),
        booleanParam(name: 'SET_BRANCH_LATEST_TAG', value: params.SET_BRANCH_LATEST_TAG),
        booleanParam(name: 'PUSH_TO_REGISTRY', value: params.PUSH_TO_REGISTRY),
        booleanParam(name: 'PUSH_TO_REGISTRY_ONLY', value: params.PUSH_TO_REGISTRY_ONLY),
        booleanParam(name: 'BUILD_CLOUD_IMAGES', value: true),
        stringParam(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
        stringParam(name: 'CIPARAM_CLEANUP_WORKSPACE', value: params.CIPARAM_CLEANUP_WORKSPACE),
        stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
        // PUBLISH_IN_MARKETPLACE will only be set during the release process (aka bw-release)
        booleanParam(name: 'PUBLISH_IN_MARKETPLACE', value: false),
        stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),
    ];

    job_parameters_use_case = [
        stringParam(name: 'USE_CASE', value: use_case),
    ];

    job_parameters_fips = [
        // build node selection in done base on USE_CASE value
        stringParam(name: 'USE_CASE', value: 'fips'),
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
        |===================================================
        """.stripMargin());

    def success = true;

    // use smart_stage to capture build result, but continue with next steps
    // this runs the consecutive stages and jobs in any case which makes it easier to re-run or fix only those distros with the next run
    // which actually failed without triggering all jobs for all but the failing distros
    success &= smart_stage(
            name: "Build Packages",
            condition: true,
            raiseOnError: false,) {
        smart_build(
            job: "${edition_base_folder}/build-cmk-deliverables",
            parameters: job_parameters
        );
    }[0]

    success &= smart_stage(
            name: "Build CMK IMAGE",
            condition: build_image,
            raiseOnError: false,) {
        smart_build(
            job: "${edition_base_folder}/build-cmk-image",
            parameters: job_parameters
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
                    job: "${edition_base_folder}/test-integration-docker",
                    parameters: job_parameters
                );
            }[0]
        },
        "Integration Test for Packages": {
            success &= smart_stage(
                name: "Integration Test for Packages",
                condition: run_int_tests,
                raiseOnError: false,) {
                smart_build(
                    job: "${edition_base_folder}/test-integration-packages",
                    parameters: job_parameters
                );
            }[0]
        },
        "Composition Test for Packages": {
            success &= smart_stage(
                    name: "Composition Test for Packages",
                    condition: run_comp_tests,
                    raiseOnError: false,) {
                smart_build(
                    job: "${edition_base_folder}/test-composition",
                    parameters: job_parameters
                );
            }[0]
        },
        "Update Test": {
            success &= smart_stage(
                    name: "Update Test",
                    condition: run_update_tests,
                    raiseOnError: false,) {
                smart_build(
                    job: "${edition_base_folder}/test-update",
                    parameters: job_parameters
                );
            }[0]
        },
        "System Tests for FIPS compliance": {
            success &= smart_stage(
                    name: "System Tests for FIPS compliance",
                    condition: run_fips_tests,
                    raiseOnError: false,) {
                build(
                    job: "${edition_base_folder}/test-integration-fips",
                    parameters: job_parameters_common + job_parameters_fips,
                    wait: false,
                );
                build(
                    job: "${edition_base_folder}/test-composition-fips",
                    parameters: job_parameters_common + job_parameters_fips,
                    wait: false,
                );
                build(
                    job: "${edition_base_folder}/test-gui-e2e-fips",
                    parameters: job_parameters_common + job_parameters_fips,
                    wait: false,
                );
            }[0]
        },
    ]);

    success &= smart_stage(
            name: "Build Packages again",
            condition: true,
            raiseOnError: false,) {
        smart_build(
            job: "${edition_base_folder}/build-cmk-deliverables",
            parameters: job_parameters
        );
    }[0]

    success &= smart_stage(
            name: "Trigger SaaS Gitlab jobs",
            condition: success && edition == "saas",
            raiseOnError: false,) {
        smart_build(
            job: "${edition_base_folder}/trigger-saas-gitlab",
            parameters: job_parameters
        );
    }[0]

    currentBuild.result = success ? "SUCCESS" : "FAILURE";
}

return this;
