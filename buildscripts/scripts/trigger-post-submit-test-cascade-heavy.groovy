#!groovy

/// file: trigger-post-submit-test-cascade-full.groovy

/// Trigger post submit test cascade of heavy jobs

def main() {
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def all_heavy_jobs = [
        "trigger-build-upload-cmk-distro-package",
        "test-gui-crawl-f12less",
        "trigger-test-gui-e2e",
        "test-integration-single-f12less",
        "test-integration-single-f12less-redfish",
        "test-composition-single-f12less",
        "test-composition-single-f12less-cme",
        "test-integration-single-f12less-cme",
        "test-update-single-f12less",
    ];

    print(
        """
        |===== CONFIGURATION ===============================
        |job_names:........... │${job_names}│
        |branch_base_folder:.. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];

    all_heavy_jobs.each { item ->
        build_for_parallel[item] = { ->
            stage(item) {
                build(
                    job: "${branch_base_folder}/${item}",
                    propagate: true,  // Raise any errors
                    parameters: [
                        string(name: "CUSTOM_GIT_REF", value: effective_git_ref),
                        string(name: "CIPARAM_OVERRIDE_BUILD_NODE", value: CIPARAM_OVERRIDE_BUILD_NODE),
                        string(name: "CIPARAM_CLEANUP_WORKSPACE", value: CIPARAM_CLEANUP_WORKSPACE),
                        string(name: "CIPARAM_BISECT_COMMENT", value: CIPARAM_BISECT_COMMENT),
                    ],
                );
            }
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;
