#!groovy

/// file: test-integration-single.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def safe_branch_name = versioning.safe_branch_name();
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch'
    )

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: ["ubuntu-20.04"],
        EDITION: "enterprise",
        VERSION: "git",
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: "test-integration-docker",
        BRANCH: safe_branch_name,
        cmk_version: versioning.get_cmk_version(safe_branch_name, "daily"),
    );
}

return this;
