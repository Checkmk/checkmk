#!groovy
/// Run composition tests

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: ???

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
    ]);

    check_environment_variables([
        "DOCKER_TAG",
        "BRANCH",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS);

    // Get the ID of the docker group from the node(!). This must not be
    // executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();
    def branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);

    // FIXME
    // CMK-1705: SLES-15 is missing xinitd and should therefore not be tested
    //DISTRO_LIST = DISTRO_LIST - ['sles-15']
    // Testing CMA is not needed
    //DISTRO_LIST = DISTRO_LIST - ['cma']

    currentBuild.description = (
        """
        |Run composition tests for<br>
        |VERSION: ${VERSION}<br>
        |EDITION: ${EDITION}<br>
        |distros: ${distros}<br>
        """.stripMargin());

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:............(local)  │${distros}│
        |===================================================
        """.stripMargin());

    // TODO: don't run make test-composition-docker but use docker.inside() instead
    stage('test cmk-docker integration') {
        testing_helper.run_make_targets(
            DOCKER_GROUP_ID: docker_group_id,
            DISTRO_LIST: distros,
            EDITION: EDITION,
            VERSION: VERSION,
            DOCKER_TAG: versioning.select_docker_tag(
                branch_name,
                DOCKER_TAG, 
                DOCKER_TAG),   // FIXME was DOCKER_TAG_DEFAULT before
            MAKE_TARGET: "test-composition-docker",
            BRANCH: branch_name,  // FIXME was BRANCH before
            cmk_version: cmk_version,
        )
    }
}
return this;

