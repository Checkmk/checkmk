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
    def safe_branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, VERSION);
    def docker_tag = versioning.select_docker_tag(
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // FIXME, 'build tag'
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD); // FIXME was DOCKER_TAG_DEFAULT before, 'folder tag'

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
        |distros:...............  │${distros}│
        |docker_tag:............  │${docker_tag}│
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
            BRANCH: versioning.branch_name(scm),
            cmk_version: cmk_version,
        )
    }
}

return this;
