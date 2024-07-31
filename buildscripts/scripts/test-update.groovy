#!groovy

/// file: test-update.groovy

def main() {
    check_job_parameters([
        ["OVERRIDE_DISTROS"],
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, "daily");

    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS, "daily_tests");
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch' returns '<BRANCH>-latest'
    );

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: "enterprise",
        VERSION: "daily",
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: "test-update-docker",
        BRANCH: safe_branch_name,
        cmk_version: cmk_version,
    );
}
return this;
