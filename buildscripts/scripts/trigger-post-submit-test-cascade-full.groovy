#!groovy

/// file: trigger-post-submit-test-cascade-full.groovy

/// Trigger post submit test cascade of heavy jobs

def main() {
    def all_heavy_jobs = [
        "trigger-build-upload-cmk-distro-package",
        "test-gui-crawl-f12less",
        "test-gui-e2e-f12less",
        "test-integration-single-f12less",
        "test-composition-single-f12less",
        "test-integration-single-f12less-cme",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |all_heavy_jobs:........... │${all_heavy_jobs}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}";

    all_heavy_jobs.each { item ->
        build_for_parallel[item] = { ->
            stage(item) {
                build(
                    job: "${base_folder}/${item}",
                    propagate: true,  // Raise any errors
                    parameters: [
                        string(name: "CUSTOM_GIT_REF", value: checkout_commit_id),
                        string(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                        string(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                        string(name: "CIPARAM_BISECT_COMMENT", value: CIPARAM_BISECT_COMMENT),
                    ],
                );
            }
        }
    }

    stage('Trigger all heavy tests') {
        parallel build_for_parallel;
    }
}

return this;
