#!groovy

/// file: test-composition.groovy

/// Run composition tests

/// Jenkins artifacts: ???
/// Other artifacts: ???
/// Depends on: ???

def main() {
    check_job_parameters([
        "EDITION",
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "USE_CASE",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def distros = versioning.get_distros(edition: EDITION, use_case: "daily_tests", override: OVERRIDE_DISTROS);

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def docker_tag = versioning.select_docker_tag(
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD); // FIXME was DOCKER_TAG_DEFAULT then DOCKER_TAG, 'folder tag'

    currentBuild.description += (
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
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            testing_helper.run_make_targets(
                DOCKER_GROUP_ID: get_docker_group_id(),
                DISTRO_LIST: distros,
                EDITION: EDITION,
                VERSION: VERSION,
                DOCKER_TAG: docker_tag,
                MAKE_TARGET: "test-composition-docker",
                BRANCH: safe_branch_name,  // FIXME was BRANCH before
                cmk_version: versioning.get_cmk_version(safe_branch_name, branch_version, VERSION),
            );
        }
    }
}

return this;
