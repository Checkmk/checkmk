#!groovy

/// file: test-update.groovy

def build_make_target(edition) {
    def prefix = "test-update-";
    def suffix = "-docker";
    switch(edition) {
        case 'enterprise':
            return prefix + "cee" + suffix
        case 'cloud':
            return prefix + "cce" + suffix
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def branch_version = versioning.get_branch_version(checkout_dir);

    check_environment_variables([
        "DOCKER_TAG",
        "EDITION"
    ]);

    def distros = versioning.configured_or_overridden_distros(EDITION, false, "daily_tests");
    def make_target = build_make_target(EDITION);

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: EDITION,
        VERSION: "daily",
        DOCKER_TAG: "master-latest",
        MAKE_TARGET: make_target,
        BRANCH: "master",
        cmk_version: versioning.get_cmk_version("master", branch_version, "daily"),
    );
}
return this;
