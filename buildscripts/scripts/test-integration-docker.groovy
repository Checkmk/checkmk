#!groovy

/// file: test-integration-docker.groovy

/// Run integration tests for the Checkmk Docker image

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: ???

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
    ]);

    check_environment_variables([
        "INTERNAL_DEPLOY_DEST",
        "INTERNAL_DEPLOY_PORT",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def artifacts_helper = load("${checkout_dir}/buildscripts/scripts/utils/upload_artifacts.groovy");

    def package_dir = "${checkout_dir}/downloaded_packages_for_docker_tests";
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    currentBuild.description += (
        """
        |Run integration tests for the Checkmk Docker image
        """.stripMargin());

    stage('cleanup old versions') {
        sh("rm -rf '${package_dir}'");
    }

    stage('Download') {
        on_dry_run_omit(LONG_RUNNING, "Download package and source") {
            artifacts_helper.download_deb(
                INTERNAL_DEPLOY_DEST,
                INTERNAL_DEPLOY_PORT,
                cmk_version_rc_aware,
                "${package_dir}/${cmk_version_rc_aware}",
                EDITION,
                "jammy",  // TODO (CMK-11568): This must be kept in sync with e.g. docker/Dockerfile
            );

            artifacts_helper.download_source_tar(
                INTERNAL_DEPLOY_DEST,
                INTERNAL_DEPLOY_PORT,
                cmk_version_rc_aware,
                "${package_dir}/${cmk_version_rc_aware}",
                EDITION,
            );
        }
    }

    // TODO: don't run make-test-docker but use docker.inside() instead
    stage('test cmk-docker integration') {
        dir("${checkout_dir}/tests") {
            def cmd = "make test-docker-docker WORKSPACE='${checkout_dir}' BRANCH='$branch_name' EDITION='$EDITION' VERSION='$cmk_version_rc_aware'";
            on_dry_run_omit(LONG_RUNNING, "RUN ${cmd}") {
                sh(cmd);
            }
        }
    }
}

return this;
