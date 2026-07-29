#!groovy

/// file: trigger-post-submit-tests-light.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def job_names = [
        "lint-repository",
        "test-bazel-lint",
        "test-format",
        "test-github-actions",
        "test-plugins-siteless",
        "test-python3-typing",
        "test-unit-all",
        // the werk test needs all git tags available in the checkout
        "test-werks",
        "trigger-test-agent-plugin-unit",
    ];
    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 1s).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn
    /// like changing order or amount of stages, which will happen with stages started `via paral
    def timeOffsetForOrder = 0;

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder:.. │${checkout_dir}│
        |force_build:......... │${force_build}│
        |job_names:........... │${job_names}│
        |safe_branch_name:.... │${safe_branch_name}│
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
                    relative_job_name: "${branch_base_folder}/light/${job_name}",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
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
