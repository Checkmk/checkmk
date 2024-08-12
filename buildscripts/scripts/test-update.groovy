#!groovy

/// file: test-update.groovy

def build_make_target(edition) {
    def prefix = "test-update-";
    def suffix = "-docker";
    switch(edition) {
        case 'enterprise':
            return prefix + "cee" + suffix;
        case 'cloud':
            return prefix + "cce" + suffix;
        default:
            error("The update tests are not yet enabled for edition: " + edition);
    }
}

def main() {
    check_job_parameters([
        ["OVERRIDE_DISTROS"],
    ]);

    check_environment_variables([
        "EDITION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, "daily");
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def edition = params.EDITION;
    def distros = versioning.configured_or_overridden_distros(EDITION, OVERRIDE_DISTROS, "daily_update_tests");
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch' returns '<BRANCH>-latest'
    );

    def make_target = build_make_target(edition);

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: edition,
        VERSION: "daily",
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: make_target,
        BRANCH: safe_branch_name,
        cmk_version: cmk_version,
    );
}

return this;
