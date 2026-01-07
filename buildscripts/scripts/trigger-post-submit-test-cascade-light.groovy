#!groovy

/// file: trigger-post-submit-test-cascade-light.groovy

void main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);

    def job_names = [
        "test-agent-plugin-unit",
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
        |===================================================
        """.stripMargin());

    def stages = job_names.collectEntries { job_name ->
        [("${job_name}") : {
            smart_stage(
                name: "Trigger ${job_name}",
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    job: "${branch_base_folder}/light/${job_name}",
                    parameters: [
                        stringParam(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
                        stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                        stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
                        stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: params.CIPARAM_CLEANUP_WORKSPACE),
                    ],
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
