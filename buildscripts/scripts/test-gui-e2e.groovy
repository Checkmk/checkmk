#!groovy

/// file: test-gui-e2e.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def safe_branch_name = versioning.safe_branch_name(scm);
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch'
    )

    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: ["ubuntu-20.04"],
        EDITION: "enterprise",
        VERSION: "git",
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: "test-gui-e2e-docker",
        BRANCH: safe_branch_name,
        cmk_version: versioning.get_cmk_version(safe_branch_name, "daily"),
    );
}

return this;
