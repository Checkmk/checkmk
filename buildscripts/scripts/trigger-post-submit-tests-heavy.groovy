#!groovy

/// file: trigger-post-submit-tests-heavy.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);

    def job_names = [
        "test-composition-pro",
        "test-composition-community",
        "test-composition-ultimatemt",
        "test-gui-crawl",
        "test-gui-e2e-cloud",
        "test-gui-e2e-pro",
        "test-gui-e2e-ultimate",
        "test-integration-agent-plugin",
        "test-integration-pro",
        "test-integration-community",
        "test-integration-cloud",
        "test-integration-redfish",
        "test-integration-ultimatemt",
        "test-integration-single-node",
        "test-plugins",
        "test-plugins-piggyback",
        "test-relay-integration",
        "test-update-cloud",
        "test-update-community",
        "test-update-pro",
        "test-update-ultimatemt",
        "test-update-community-pro",
        "test-update-pro-ultimate",
        "test-update-pro-ultimatemt",
        "winagt-test-mk-oracle",
    ];

    def trigger_xss_crawl = false;
    // The time 2000 has been chosen to not collide with the CI maintenance window
    if (Calendar.getInstance().get(Calendar.HOUR_OF_DAY) == 20) {
        trigger_xss_crawl = true;
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:.... │${safe_branch_name}│
        |job_names:........... │${job_names}│
        |branch_base_folder:.. │${checkout_dir}│
        |trigger_xss_crawl:... │${trigger_xss_crawl}│
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
                    force_build: params.DISABLE_JENKINS_CACHE == true,
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

    stages += [("test-xss-crawl") : {
        smart_stage(
            name: "Trigger test-xss-crawl",
            condition: trigger_xss_crawl,
        ) {
            smart_build(
                // see global-defaults.yml, needs to run in minimal container
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${branch_base_folder}/heavy/test-xss-crawl",
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

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
