#!groovy

/// file: trigger-post-submit-tests-light.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def force_build = params.DISABLE_JENKINS_CACHE == true;

    def job_names = [
        "trigger-test-agent-plugin-unit",
        "test-bazel-lint",
        "test-format",
        "test-github-actions",
        "test-groovy-lint",
        "test-integration-agent-plugin",
        "test-plugins-siteless",
        "test-python3-astrein",
        "test-python3-bandit",
        "test-python3-code-quality",
        "test-python3-ruff",
        "test-python3-typing",
        "test-python3-unit-all",
        "test-shell-unit",
        "test-shellcheck_agents",
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

    def stages = job_names.collectEntries { job_name ->
        [("${job_name}") : {
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
