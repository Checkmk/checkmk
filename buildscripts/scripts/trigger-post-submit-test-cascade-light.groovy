#!groovy

/// file: trigger-post-submit-test-cascade-light.groovy

/// Trigger post submit test cascade of lightweight jobs

def main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def job_names = [
        "test-python3-pylint",
        "test-python3-ruff",
        "test-python3-bandit",
        "test-agent-plugin-unit",
        "test-python3-code-quality",
        "test-python3-format",
        "test-python3-typing",
        "test-bazel-lint",
        "test-bazel-format",
        "test-groovy-lint",
        "test-shellcheck_agents",
        "test-shell_format",
        "test-shell-unit",
        "test-python3-unit-all",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |job_names:........... │${job_names}│
        |branch_base_folder:.. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    currentBuild.result = parallel(
        job_names.collectEntries { job_name ->
            [("${job_name}") : {
                stage("Trigger ${job_name}") {
                    smart_build(
                        job: "${branch_base_folder}/${job_name}",
                        parameters: [
                            stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                            stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                            stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                            stringParam(name: "CIPARAM_BISECT_COMMENT", value: CIPARAM_BISECT_COMMENT),
                        ],
                    );
                }
            }
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;
