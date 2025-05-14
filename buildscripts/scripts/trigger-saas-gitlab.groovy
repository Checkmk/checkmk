#!groovy

/// file: trigger-saas-gitlab.groovy

/// Trigger job chains in the saas project on gitlab

def main() {
    check_job_parameters([
        "VERSION",
    ]);
    check_environment_variables([
        "GITLAB_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......  │${safe_branch_name}│
        |cmk_version:...........  │${cmk_version}
        |===================================================
        """.stripMargin());

    // Jobs in saas use the version tag to read images and parse version information
    withCredentials([
        string(
            credentialsId: "GITLAB_TRIGGER_TOKEN",
            variable:"GITLAB_TRIGGER_TOKEN"),
    ]) {
        sh("""
            curl -X POST \
            --fail \
            -F token=${GITLAB_TRIGGER_TOKEN} \
            -F ref="main" \
            -F variables[BUILD_CMK_TAG]="${cmk_version}" \
            -F variables[BUILD_CSE]="true" \
            ${GITLAB_URL}/api/v4/projects/3/trigger/pipeline
        """);
    }
}

return this;
