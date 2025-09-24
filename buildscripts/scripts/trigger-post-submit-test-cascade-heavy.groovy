#!groovy

/// file: trigger-post-submit-test-cascade-full.groovy

def main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);

    def job_names = [
        "test-composition-single-f12less",
        "test-composition-single-f12less-cme",
        "test-composition-single-f12less-cre",
        "test-gui-crawl-f12less",
        "test-gui-e2e-f12less-cce",
        "test-gui-e2e-f12less-cee",
        "test-gui-e2e-f12less-cse",
        "test-integration-agent-plugin",
        "test-integration-single-f12less",
        "test-integration-single-f12less-cme",
        "test-integration-single-f12less-cre",
        "test-integration-single-f12less-redfish",
        "test-plugins",
        "test-plugins-piggyback",
        "test-plugins-siteless",
        "test-update-single-f12less",
        "test-update-single-f12less-cce",
        "test-update-single-f12less-cme",
        "test-update-single-f12less-cre",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:.... │${safe_branch_name}│
        |job_names:........... │${job_names}│
        |branch_base_folder:.. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    def stages = job_names.collectEntries { job_name ->
        [("${job_name}") : {
            smart_stage(
                name: "Trigger ${job_name}",
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/heavy/${job_name}",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
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
