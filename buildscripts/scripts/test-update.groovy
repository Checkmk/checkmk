#!groovy

/// file: test-update.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    check_environment_variables([
        "DOCKER_TAG",
    ]);

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: ["ubuntu-20.04", "ubuntu-22.04", "debian-11", "centos-8", "sles-15sp4"],
        EDITION: "enterprise",
        VERSION: "daily",
        DOCKER_TAG: "master-latest",
        MAKE_TARGET: "test-update-docker",
        BRANCH: "master",
        cmk_version: versioning.get_cmk_version("master", "daily"),
    );
}
return this;
