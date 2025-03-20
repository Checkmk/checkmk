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

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS, "daily_tests");

    def safe_branch_name = versioning.safe_branch_name();
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (VERSION == "daily") ? safe_branch_name : branch_version;
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );
    def cmk_version_rc_aware =  versioning.get_cmk_version(safe_branch_name, VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

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
        |distros:...................│${distros}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |===================================================
        """.stripMargin());

    // TODO: don't run make test-composition-docker but use docker.inside() instead
    stage('test cmk-docker integration') {
        testing_helper.run_make_targets(
            DOCKER_GROUP_ID: get_docker_group_id(),
            DISTRO_LIST: distros,
            EDITION: EDITION,
            VERSION: VERSION,
            DOCKER_TAG: docker_tag,
            MAKE_TARGET: "test-composition-docker",
            BRANCH: branch_name,
            cmk_version: cmk_version,
        );
    }
}

return this;
