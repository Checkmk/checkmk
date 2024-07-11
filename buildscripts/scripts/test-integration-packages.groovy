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

    def distros = versioning.get_distros(edition: EDITION, use_case: "daily_tests", override: OVERRIDE_DISTROS);
    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, branch_version, VERSION);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // FIXME, 'build tag'
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // FIXME was DOCKER_TAG_DEFAULT before, 'folder tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    currentBuild.description += (
        """
        |Run integration tests for packages<br>
        |VERSION: ${VERSION}<br>
        |EDITION: ${EDITION}<br>
        |safe_branch_name: ${safe_branch_name}<br>
        |cmk_version: ${cmk_version}<br>
        |distros: ${distros}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |safe_branch_name:......  │${safe_branch_name}│
        |docker_tag:............  │${docker_tag}│
        |distros:...............  │${distros}│
        |cmk_version:...........  │${cmk_version}
        |===================================================
        """.stripMargin());

    stage('test integration') {  // TODO should not be needed
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
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
            );
        }
    }
}

return this;
