#!groovy

/// file: test-update.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    check_job_parameters([
        ["OVERRIDE_DISTROS"],
    ]);

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS, "daily_tests");

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: "enterprise",
        VERSION: "daily",
        DOCKER_TAG: "2.2.0-latest",
        MAKE_TARGET: "test-update-docker",
        BRANCH: "2.2.0",
        cmk_version: versioning.get_cmk_version("2.2.0", "daily"),
    );
}
return this;
