#!groovy

/// file: trigger-pre-submit-test-cascade-medium.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def do_rebase = params.CIPARAM_GATED_TRIGGER_REBASE;

    def edition_medium_chain = "pro";
    def distro_medium_chain = "ubuntu-24.04";

    def job_names = [
        "test-composition-${edition_medium_chain}",
        "test-integration-${edition_medium_chain}",
    ];

    // rebase_onto: tip of target branch, computed below if CIPARAM_GATED_TRIGGER_REBASE is set.
    def rebase_onto = "";

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:.. │${safe_branch_name}│
        |job_names:......... │${job_names}│
        |branch_base_folder: │${branch_base_folder}│
        |force_build:....... │${force_build}│
        |do_rebase:......... │${do_rebase}│
        |===================================================
        """.stripMargin());

    // This avoids the pods for the tests waiting for the package to be built.
    // The test pods are expensive and would only idle in that time.
    inside_container_minimal(safe_branch_name: safe_branch_name) {
        smart_stage(
            name: "Compute rebase anchors",
            condition: do_rebase,
            raiseOnError: true,
        ) {
            rebase_onto = versioning.compute_rebase_onto(safe_branch_name);
        }

        smart_stage(
            name: "Pre-build needed package",
            raiseOnError: true,
        ) {
            smart_build(
                // see global-defaults.yml, needs to run in minimal container
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${branch_base_folder}/builders/trigger-cmk-distro-package",
                build_params: [
                    CUSTOM_GIT_REF: effective_git_ref,
                    EDITION: edition_medium_chain,
                    DISTRO: distro_medium_chain,
                    DISABLE_CACHE: params.DISABLE_CACHE,
                    FAKE_ARTIFACTS: true,
                    CIPARAM_GATED_REBASE_ONTO: rebase_onto,
                ],
                build_params_no_check: [
                    CIPARAM_OVERRIDE_BUILD_NODE      : params.CIPARAM_OVERRIDE_BUILD_NODE,
                    CIPARAM_CLEANUP_WORKSPACE        : params.CIPARAM_CLEANUP_WORKSPACE,
                    CIPARAM_BISECT_COMMENT           : params.CIPARAM_BISECT_COMMENT,
                    CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                ],
                no_remove_others: true, // do not delete other files in the dest dir
                download: false,    // use copyArtifacts to avoid nested directories
            );
        }
    }

    def stages = job_names.collectEntries { job_name ->
        [("${job_name}") : {
            smart_stage(
                name: "Trigger ${job_name}",
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    force_build: force_build,
                    relative_job_name: "${branch_base_folder}/cv/${job_name}",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        EDITION: edition_medium_chain,
                        DISTRO: distro_medium_chain,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_ARTIFACTS: true,
                        // if there is a test filter specified on make target level, the last one in the list of pytest arguments will
                        // overwrite all previous ones. Place all required test filters in one place and connect them with "and"
                        // "TEST_FILTER" is prepended to the pytest call and thereby always the first source of settings and so it is
                        // overruled if there is an additional test filter set later in the list of pytest args
                        // Remember to quote a chain of filters to prevent word splitting
                        // Setting "-m medium_test_chain" will cause special handling in "test-integration-single.groovy"
                        TEST_FILTER: '-m medium_test_chain',
                        CIPARAM_GATED_REBASE_ONTO: rebase_onto,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
