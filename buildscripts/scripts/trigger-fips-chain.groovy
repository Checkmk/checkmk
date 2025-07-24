#!groovy

/// file: trigger-fips-chain.groovy

import java.time.LocalDate

def main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "FAKE_WINDOWS_ARTIFACTS",
    ]);


    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    /// NOTE: this way ALL parameter are being passed through..
    def job_parameters = [
        stringParam(name: 'EDITION', value: params.EDITION),
        stringParam(name: 'VERSION', value: params.VERSION),
        stringParam(name: 'OVERRIDE_DISTROS', value: params.OVERRIDE_DISTROS),
        booleanParam(name: 'FAKE_WINDOWS_ARTIFACTS', value: params.FAKE_WINDOWS_ARTIFACTS),
        stringParam(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
        stringParam(name: 'CIPARAM_CLEANUP_WORKSPACE', value: params.CIPARAM_CLEANUP_WORKSPACE),
        stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
        stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),

        /// Hardcode the USE_CASE to fips, because this is our only use case here
        stringParam(name: 'USE_CASE', value: 'fips'),
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |edition:............... │${params.EDITION}│
        |version:............... │${params.VERSION}│
        |override_distros:...... │${params.OVERRIDE_DISTROS}│
        |fake_windows_artifacts: │${params.FAKE_WINDOWS_ARTIFACTS}│
        |custom_git_ref:........ │${effective_git_ref}│
        |===================================================
        """.stripMargin());

    def success = true;

    // We currently run those tests sequential due to resource constraints.

    // use smart_stage to capture build result, but continue with next steps
    success &= smart_stage(
            name: "Run composition tests on FIPS",
            condition: true,
            raiseOnError: false,) {
        smart_build(
            job: "${branch_base_folder}/fips/test-composition-fips",
            parameters: job_parameters
        );
    }[0]

    success &= smart_stage(
            name: "Run GUI End-to-End tests on FIPS",
            condition: true,
            raiseOnError: false,) {
        smart_build(
            job: "${branch_base_folder}/fips/test-gui-e2e-fips ",
            parameters: job_parameters
        );
    }[0]

    success &= smart_stage(
            name: "Run integration tests on FIPS",
            condition: true,
            raiseOnError: false,) {
        smart_build(
            job: "${branch_base_folder}/fips/test-integration-fips",
            parameters: job_parameters
        );
    }[0]

    currentBuild.result = success ? "SUCCESS" : "FAILURE";
}

return this;
