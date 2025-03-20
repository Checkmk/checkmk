#!groovy

/// file: test-integration-packages.groovy

/// Run integration tests for the Checkmk Docker image

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "USE_CASE",
    ]);

    check_environment_variables([
        "BRANCH",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS, "daily_tests");
    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // FIXME, 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    currentBuild.description = (
        """
        |Run integration tests for packages<br>
        |VERSION: ${VERSION}<br>
        |EDITION: ${EDITION}<br>
        |distros: ${distros}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:.................  │${distros}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:........  │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:..............  │${docker_tag}│
        |===================================================
        """.stripMargin());

    stage('test integration') {  // TODO should not be needed
        // TODO: don't run make test-integration-docker but use docker.inside() instead
        testing_helper.run_make_targets(
            // Get the ID of the docker group from the node(!). This must not be
            // executed inside the container (as long as the IDs are different)
            DOCKER_GROUP_ID: get_docker_group_id(),
            DISTRO_LIST: distros,
            EDITION: EDITION,
            VERSION: VERSION,
            DOCKER_TAG: docker_tag,
            MAKE_TARGET: "test-integration-docker",
            BRANCH: branch_name,
            cmk_version: cmk_version,
        )
    }
}

return this;
