#!groovy

/// file: trigger-cmk-build-chain.groovy

/// This job will trigger other jobs

/// Jenkins artifacts:  Those of child jobs
/// Other artifacts:    Those of child jobs
/// Depends on:         Nothing

import java.time.LocalDate

def main() {

    /// make sure the listed parameters are set
    check_job_parameters([
        "VERSION",
        "OVERRIDE_DISTROS",
        "SKIP_DEPLOY_TO_WEBSITE",
        "DEPLOY_TO_WEBSITE_ONLY",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
        "SET_LATEST_TAG",
        "SET_BRANCH_LATEST_TAG",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
    ]);

    def edition = JOB_BASE_NAME.split("-")[-1];
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/nightly-${edition}";
    def use_case = LocalDate.now().getDayOfWeek() in ["SATURDAY", "SUNDAY"] ? "weekly" : "daily"

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters = [
        stringParam(name: 'EDITION', value: edition),

        // TODO perhaps use `params` + [EDITION]?
        // FIXME: all parameters from all triggered jobs have to be handled here
        stringParam(name: 'VERSION', value: VERSION),
        stringParam(name: 'OVERRIDE_DISTROS', value: params.OVERRIDE_DISTROS),
        booleanParam(name: 'SKIP_DEPLOY_TO_WEBSITE', value: params.SKIP_DEPLOY_TO_WEBSITE),
        booleanParam(name: 'DEPLOY_TO_WEBSITE_ONLY', value: params.DEPLOY_TO_WEBSITE_ONLY),
        booleanParam(name: 'FAKE_WINDOWS_ARTIFACTS', value: params.FAKE_WINDOWS_ARTIFACTS),
        stringParam(name: 'CIPARAM_OVERRIDE_DOCKER_TAG_BUILD', value: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD),
        booleanParam(name: 'SET_LATEST_TAG', value: params.SET_LATEST_TAG),
        booleanParam(name: 'SET_BRANCH_LATEST_TAG', value: params.SET_BRANCH_LATEST_TAG),
        booleanParam(name: 'PUSH_TO_REGISTRY', value: params.PUSH_TO_REGISTRY),
        booleanParam(name: 'PUSH_TO_REGISTRY_ONLY', value: params.PUSH_TO_REGISTRY_ONLY),
        booleanParam(name: 'BUILD_CLOUD_IMAGES', value: true),
        stringParam(name: 'CUSTOM_GIT_REF', value: params.CUSTOM_GIT_REF),
        stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),
        stringParam(name: 'CIPARAM_CLEANUP_WORKSPACE', value: params.CIPARAM_CLEANUP_WORKSPACE),
        stringParam(name: 'CIPARAM_BISECT_COMMENT', value: params.CIPARAM_BISECT_COMMENT),
        // PUBLISH_IN_MARKETPLACE will only be set during the release process (aka bw-release)
        booleanParam(name: 'PUBLISH_IN_MARKETPLACE', value: false),
        stringParam(name: 'USE_CASE', value: use_case),
    ];

    // TODO we should take this list from a single source of truth
    assert edition in ["enterprise", "raw", "managed", "cloud"] : (
        "Do not know edition '${edition}' extracted from ${JOB_BASE_NAME}")

    def build_image = true;

    def run_integration_tests = true;
    def run_image_tests = true;
    def run_update_tests = (edition in ["enterprise"]);

    print(
        """
        |===== CONFIGURATION ===============================
        |edition:............... │${edition}│
        |base_folder:........... │${base_folder}│
        |build_image:........... │${build_image}│
        |run_integration_tests:. │${run_integration_tests}│
        |run_image_tests:....... │${run_image_tests}│
        |run_update_tests:...... │${run_update_tests}│
        |use_case:.............. │${use_case}│
        |===================================================
        """.stripMargin());

    def success = true;

    stage("Build Packages") {
        build(job: "${base_folder}/build-cmk-packages", parameters: job_parameters);
    }

    success &= smart_stage(
            name: "Build CMK IMAGE",
            condition: build_image,
            raiseOnError: false) {
        build(job: "${base_folder}/build-cmk-image", parameters: job_parameters);
    }

    parallel([
        "Integration Test for Docker Container": {
            success &= smart_stage(
                    name: "Integration Test for Docker Container",
                    condition: run_image_tests,
                    raiseOnError: false) {
                build(job: "${base_folder}/test-integration-docker", parameters: job_parameters);
            }
        },

        "Composition Test for Packages": {
            success &= smart_stage(
                    name: "Composition Test for Packages",
                    condition: run_integration_tests,
                    raiseOnError: false) {
                build(job: "${base_folder}/test-composition", parameters: job_parameters);
            }
        }
    ])

    success &= smart_stage(
            name: "Integration Test for Packages",
            condition: run_integration_tests,
            raiseOnError: false) {
        build(job: "${base_folder}/test-integration-packages", parameters: job_parameters);
    }

    success &= smart_stage(
            name: "Update Test",
            condition: run_update_tests,
            raiseOnError: false) {
        build(job: "${base_folder}/test-update", parameters: job_parameters);
    }

    currentBuild.result = success ? "SUCCESS" : "FAILURE";
}

return this;
