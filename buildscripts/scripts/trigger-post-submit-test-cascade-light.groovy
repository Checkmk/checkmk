#!groovy

/// file: trigger-post-submit-test-cascade-light.groovy

/// Trigger post submit test cascade of lightweight jobs

def main() {
    def job_names = [
        "test-python3-pylint",
        "test-python3-bandit",
        "test-agent-plugin-unit",
        "test-python3-code-quality",
        "test-python3-format",
        "test-python3-typing",
        "test-javascript-format",
        "test-javascript-build",
        "test-javascript-lint",
        "test-typescript-types",
        "test-css-format",
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
        |job_names:..... │${job_names}│
        |checkout_dir:.. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}";

    currentBuild.result = parallel(
        job_names.collectEntries { job_name ->
            [("${job_name}") : {
                stage("Trigger ${job_name}") {
                    smart_build(
                        job: "${base_folder}/${job_name}",
                        parameters: [
                            stringParam(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                            stringParam(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                            stringParam(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                            stringParam(name: "CIPARAM_BISECT_COMMENT", value: CIPARAM_BISECT_COMMENT),
                        ],
                    );
                }
            }]
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;
