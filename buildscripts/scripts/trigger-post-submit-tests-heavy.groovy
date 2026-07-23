#!groovy

/// file: trigger-post-submit-tests-heavy.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def disable_cache = params.DISABLE_CACHE;
    def disable_signing = params.DISABLE_CMK_DISTRO_PACKAGE_SIGNING;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def job_names = [
        "test-system-multisite-pro",
        "test-system-multisite-community",
        "test-system-multisite-ultimatemt",
        "test-system-gui-crawl",
        "test-system-gui-cloud",
        "test-system-gui-pro",
        "test-system-gui-ultimate",
        "test-system-mk-oracle",
        "test-system-redfish",
        "test-system-singlesite-community",
        "test-system-singlesite-cloud",
        "test-system-singlesite-pro",
        "test-system-singlesite-ultimatemt",
        "test-system-singlesite-single-node",
        "test-system-plugins",
        "test-system-plugins-piggyback",
        "test-system-relay",
        "test-system-update-cloud",
        "test-system-update-community",
        "test-system-update-pro",
        "test-system-update-ultimatemt",
        "test-system-update-community-pro",
        "test-system-update-pro-ultimate",
        "test-system-update-pro-ultimatemt",
        "winagt-test-mk-oracle",
    ];
    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 1s).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn
    /// like changing order or amount of stages, which will happen with stages started `via paral
    def timeOffsetForOrder = 0;
    def trigger_xss_crawl = false;

    // The time 2000 has been chosen to not collide with the CI maintenance window
    if (Calendar.getInstance().get(Calendar.HOUR_OF_DAY) == 20) {
        trigger_xss_crawl = true;
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder:.. │${checkout_dir}│
        |disable_signing:..... │${disable_signing}│
        |fake_artifacts:...... │${fake_artifacts}│
        |force_build:......... │${force_build}│
        |job_names:........... │${job_names}│
        |safe_branch_name:.... │${safe_branch_name}│
        |trigger_xss_crawl:... │${trigger_xss_crawl}│
        |===================================================
        """.stripMargin());

    def stages = job_names.collectEntries { job_name ->
        [("${job_name}") : {
            sleep(1 * timeOffsetForOrder++);

            smart_stage(
                name: "Trigger ${job_name}",
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    force_build: force_build,
                    relative_job_name: "${branch_base_folder}/heavy/${job_name}",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        FAKE_ARTIFACTS: fake_artifacts,
                        DISABLE_CACHE: disable_cache,
                        DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
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

    stages += [("test-system-gui-crawl-xss") : {
        smart_stage(
            name: "Trigger test-system-gui-crawl-xss",
            condition: trigger_xss_crawl,
        ) {
            smart_build(
                // see global-defaults.yml, needs to run in minimal container
                use_upstream_build: true,
                force_build: force_build,
                relative_job_name: "${branch_base_folder}/heavy/test-system-gui-crawl-xss",
                build_params: [
                    CUSTOM_GIT_REF: effective_git_ref,
                    FAKE_ARTIFACTS: fake_artifacts,
                    DISABLE_CACHE: disable_cache,
                    DISABLE_CMK_DISTRO_PACKAGE_SIGNING: disable_signing,
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
