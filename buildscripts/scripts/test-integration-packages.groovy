#!groovy
/// Run integration tests for the Checkmk Docker image

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
        "BRANCH",
        "DOCKER_TAG",
        "DOCKER_TAG_DEFAULT",
    ]);
    
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS);
    def branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(branch_name, VERSION);
    def docker_tag = versioning.select_docker_tag(
        branch_name,
        env.DOCKER_TAG,  // FIXME
        env.DOCKER_TAG_DEFAULT);

    // FIXME
    // CMK-1705: SLES-15 is missing xinitd and should therefore not be tested
    //DISTRO_LIST = DISTRO_LIST - ['sles-15']
    // Testing CMA is not needed
    //DISTRO_LIST = DISTRO_LIST - ['cma']

    //def DOCKER_TAG_DEFAULT
    //def BRANCH
    //withFolderProperties{
    //    DOCKER_TAG_DEFAULT = env.DOCKER_TAG_FOLDER
    //    BRANCH = env.BRANCH
    //}

    // Get the ID of the docker group from the node(!). This must not be
    // executed inside the container (as long as the IDs are different)
    def docker_group_id = get_docker_group_id();

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
            DOCKER_GROUP_ID: docker_group_id,
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

