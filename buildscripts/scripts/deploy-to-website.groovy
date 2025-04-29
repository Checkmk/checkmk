#!groovy

/// file: deploy_to_website.groovy

def main() {
    check_job_parameters([
        ["VERSION", true],
        ["UPDATE_LATEST_BOM_SYMLINKS", true],
        ["UPDATE_BRANCH_LATEST_BOM_SYMLINKS", true],
        ["CIPARAM_REMOVE_RC_CANDIDATES", true],
    ]);

    check_environment_variables([
        "WEB_DEPLOY_PORT",
        "WEB_DEPLOY_URL",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);

    print(
        """
        |===== CONFIGURATION ===============================
        |VERSION:...................... │${params.VERSION}│
        |CIPARAM_REMOVE_RC_CANDIDATES:. │${params.CIPARAM_REMOVE_RC_CANDIDATES}│
        |cmk_version_rc_aware:......... │${cmk_version_rc_aware}│
        |WEB_DEPLOY_PORT:.............. │${env.WEB_DEPLOY_PORT}│
        |WEB_DEPLOY_URL:............... │${env.WEB_DEPLOY_URL}│
        |===================================================
        """.stripMargin());

    smart_stage(
        name: "Deploy to website",
    ) {
        artifacts_helper.deploy_to_website(cmk_version_rc_aware);
    }

    smart_stage(
        name: "Update bill-of-materials symlinks",
        condition: params.UPDATE_BRANCH_LATEST_BOM_SYMLINKS || params.UPDATE_LATEST_BOM_SYMLINKS,
    ) {
        artifacts_helper.update_bom_symlinks(
            cmk_version_rc_aware,
            branch_latest=params.UPDATE_BRANCH_LATEST_BOM_SYMLINKS,
            latest=params.UPDATE_LATEST_BOM_SYMLINKS
        );
    }

    smart_stage(
        name: "Cleanup RC candicates",
        condition: params.CIPARAM_REMOVE_RC_CANDIDATES,
    ) {
        artifacts_helper.cleanup_rc_candidates_of_version(cmk_version_rc_aware);
    }
}

return this;
