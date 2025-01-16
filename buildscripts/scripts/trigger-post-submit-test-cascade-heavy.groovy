#!groovy

/// file: trigger-post-submit-test-cascade-full.groovy

/// Trigger post submit test cascade of heavy jobs

def main() {
    def job_names = [
        "trigger-build-upload-cmk-distro-package",
        "test-gui-crawl-f12less",
        "test-gui-e2e-f12less",
        "test-integration-single-f12less",
        "test-composition-single-f12less",
        "test-integration-single-f12less-cme",
        "test-update-single-f12less",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |job_names:........... │${job_names}│
        |checkout_dir:........ │${checkout_dir}│
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
