#!groovy

/// file: trigger-cmk-build-chain.groovy

/// This job will trigger other jobs

/// Jenkins artifacts:  Those of child jobs
/// Other artifacts:    Those of child jobs
/// Depends on:         Nothing

def main() {

    /// make sure the listed parameters are set
    check_job_parameters([
        "VERSION",
        "OVERRIDE_DISTROS",
        "SKIP_DEPLOY_TO_WEBSITE",
        "DEPLOY_TO_WEBSITE_ONLY",
        "DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
        "SET_LATEST_TAG",
        "SET_BRANCH_LATEST_TAG",
        "PUSH_TO_REGISTRY",
        "PUSH_TO_REGISTRY_ONLY",
    ]);

    def edition = JOB_BASE_NAME.split("-")[-1];
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/nightly-${edition}";

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters = [
        [$class: 'StringParameterValue', name: 'EDITION', value: edition],

        // TODO perhaps use `params` + [EDITION]?
        // FIXME: all parameters from all triggered jobs have to be handled here
        [$class: 'StringParameterValue',  name: 'VERSION', value: VERSION],
        [$class: 'StringParameterValue',  name: 'OVERRIDE_DISTROS', value: params.OVERRIDE_DISTROS],
        [$class: 'BooleanParameterValue', name: 'SKIP_DEPLOY_TO_WEBSITE', value: params.SKIP_DEPLOY_TO_WEBSITE],
        [$class: 'BooleanParameterValue', name: 'DEPLOY_TO_WEBSITE_ONLY', value: params.DEPLOY_TO_WEBSITE_ONLY],
        [$class: 'BooleanParameterValue', name: 'FAKE_WINDOWS_ARTIFACTS', value: params.FAKE_WINDOWS_ARTIFACTS],
        [$class: 'StringParameterValue',  name: 'DOCKER_TAG', value: DOCKER_TAG],
        [$class: 'StringParameterValue',  name: 'DOCKER_TAG_BUILD', value: params.DOCKER_TAG_BUILD],
        [$class: 'BooleanParameterValue', name: 'SET_LATEST_TAG', value: params.SET_LATEST_TAG],
        [$class: 'BooleanParameterValue', name: 'SET_BRANCH_LATEST_TAG', value: params.SET_BRANCH_LATEST_TAG],
        [$class: 'BooleanParameterValue', name: 'PUSH_TO_REGISTRY', value: params.PUSH_TO_REGISTRY],
        [$class: 'BooleanParameterValue', name: 'PUSH_TO_REGISTRY_ONLY', value: params.PUSH_TO_REGISTRY_ONLY],
    ];

    // TODO we should take this list from a single source of truth
    assert edition in ["enterprise", "raw", "managed", "cloud"] : (
        "Do not know edition '${edition}' extracted from ${JOB_BASE_NAME}")

    def build_image = true;
    def build_cloud_images = edition == "cloud";

    def run_integration_tests = true;
    def run_image_tests = true;
    def run_update_tests = (edition in ["enterprise"]);

    print(
        """
        |===== CONFIGURATION ===============================
        |edition:............... │${edition}│
        |base_folder:........... │${base_folder}│
        |build_image:........... │${build_image}│
        |build_cloud_images:.... │${build_cloud_images}│
        |run_integration_tests:. │${run_integration_tests}│
        |run_image_tests:....... │${run_image_tests}│
        |run_update_tests:...... │${run_update_tests}│
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

    success &= smart_stage(
            name: "Build Cloud Images",
            condition: build_cloud_images,
            raiseOnError: false) {
        build(job: "${base_folder}/build-cmk-cloud-images", parameters: job_parameters);
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
