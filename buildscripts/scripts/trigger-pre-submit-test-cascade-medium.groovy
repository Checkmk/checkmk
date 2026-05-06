#!groovy

/// file: trigger-post-submit-test-cascade-medium.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def edition_medium_chain = "pro";
    def distro_medium_chain = "ubuntu-24.04";

    def job_names = [
        "test-composition-single-f12less-k8s",
        // TODO: Switch to -k8s version
        "test-integration-single-f12less",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:.... │${safe_branch_name}│
        |job_names:........... │${job_names}│
        |branch_base_folder:.. │${checkout_dir}│
        |force_build:......... │${force_build}│
        |===================================================
        """.stripMargin());

    // This avoids the pods for the tests waiting for the package to be built.
    // The test pods are expensive and would only idle in that time.
    inside_container_minimal(safe_branch_name: safe_branch_name) {
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
                    relative_job_name: "${branch_base_folder}/builders/${job_name}",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        EDITION: edition_medium_chain,
                        DISTRO: distro_medium_chain,
                        DISABLE_CACHE: params.DISABLE_CACHE,
                        FAKE_ARTIFACTS: true,
                        TEST_FILTER: "-m medium_test_chain",
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
