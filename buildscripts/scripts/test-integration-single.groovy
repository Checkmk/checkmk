#!groovy

/// file: test-integration-single.groovy

def main() {
    check_environment_variables([
        "DOCKER_TAG",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def distros = ["ubuntu-20.04"];
    def safe_branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, "daily");
    def docker_tag = versioning.select_docker_tag(
            safe_branch_name,
            "",
            "")   // FIXME was DOCKER_TAG_DEFAULT before

    currentBuild.description += (
        """
        |Run integration tests for packages<br>
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

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: "enterprise",
        VERSION: "git",
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: "test-integration-docker",
        BRANCH: versioning.branch_name(scm),
        cmk_version: cmk_version,
    );
}
return this;
