#!groovy

/// file: trigger-fips-chain.groovy

void main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "EDITION",
        "FAKE_ARTIFACTS",
        "OVERRIDE_DISTROS",
        "VERSION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    /// NOTE: this way ALL parameter are being passed through..
    /// DISTRO is set lazily below, once the FIPS distro list has been resolved.
    def job_parameters = [
        EDITION: params.EDITION,
        VERSION: params.VERSION,
        OVERRIDE_DISTROS: params.OVERRIDE_DISTROS,
        FAKE_ARTIFACTS: fake_artifacts,
        DISABLE_CACHE: disable_cache,
        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
        CUSTOM_GIT_REF: effective_git_ref,

        /// Hardcode the USE_CASE to fips, because this is our only use case here
        USE_CASE: 'fips',
    ];
    def job_parameters_no_check = [
        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
    ];
    def success = true;

    print(
        """
        |===== CONFIGURATION ===============================
        |custom_git_ref:........ │${effective_git_ref}│
        |disable_cache:......... │${disable_cache}│
        |disable_signing:....... │${disable_signing}│
        |edition:............... │${params.EDITION}│
        |fake_artifacts:........ │${fake_artifacts}│
        |force_build:........... │${force_build}│
        |override_distros:...... │${params.OVERRIDE_DISTROS}│
        |safe_branch_name:...... │${safe_branch_name}│
        |version:............... │${params.VERSION}│
        |===================================================
        """.stripMargin());

    // We currently run those tests sequential due to resource constraints.
    // use smart_stage to capture build result, but continue with next steps
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        /// Resolve the FIPS distro list from editions.yml (or OVERRIDE_DISTROS if supplied).
        /// test-gui-e2e-fips is a single-distro runner, so DISTRO must be a concrete value.
        def fips_distros = versioning.get_distros(
            edition: params.EDITION,
            use_case: "fips",
            override: params.OVERRIDE_DISTROS,
        );
        assert fips_distros : "No FIPS distros resolved for edition '${params.EDITION}'";
        job_parameters.DISTRO = fips_distros.first();

        success &= smart_stage(
                name: "Run composition tests on FIPS",
                condition: true,
                raiseOnError: false,) {
            smart_build(
                use_upstream_build: true,
                force_build: force_build,
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
                force_build: force_build,
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
                force_build: force_build,
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
