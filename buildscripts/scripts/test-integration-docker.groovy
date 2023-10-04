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

    def package_dir = "${checkout_dir}/packages";
    def branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);

    print(
        """
        |===== CONFIGURATION ===============================
        |cmk_version:....................(local)  │${cmk_version}│
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
                cmk_version,
                "${package_dir}/${cmk_version}",
                EDITION,
                "jammy",  // TODO (CMK-11568): This must be kept in sync with e.g. docker/Dockerfile
            );

            artifacts_helper.download_source_tar(
                INTERNAL_DEPLOY_DEST,
                INTERNAL_DEPLOY_PORT,
                cmk_version,
                "${package_dir}/${cmk_version}",
                EDITION,
            );
        }
    }

    // TODO: don't run make-test-docker but use docker.inside() instead
    stage('test cmk-docker integration') {
        dir("${checkout_dir}/tests") {
            def cmd = "make test-docker-docker WORKSPACE='${checkout_dir}' BRANCH='$branch_name' EDITION='$EDITION' VERSION='$cmk_version'";
            on_dry_run_omit(LONG_RUNNING, "RUN ${cmd}") {
                sh(cmd);
            }
        }
    }
}

return this;
