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
        "VERSION",
        "OVERRIDE_DISTROS",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    check_environment_variables([
        "EDITION",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");
    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (params.VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def edition = params.EDITION;
    def all_distros = versioning.get_distros(override: "all");
    def distros = versioning.get_distros(edition: edition, use_case: "daily_update_tests", override: OVERRIDE_DISTROS);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def make_target = build_make_target(edition);

    print(
        """
        |===== CONFIGURATION ===============================
        |all_distros:.............. │${all_distros}│
        |distros:.................. │${distros}│
        |edition:.................. │${edition}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |checkout_dir:............. │${checkout_dir}│
        |branch_base_folder:....... │${branch_base_folder}│
        |make_target:.............. |${make_target}|
        |===================================================
        """.stripMargin());

    testing_helper.run_make_targets(
        DOCKER_GROUP_ID: get_docker_group_id(),
        DISTRO_LIST: distros,
        EDITION: edition,
        VERSION: VERSION,
        DOCKER_TAG: docker_tag,
        MAKE_TARGET: make_target,
        BRANCH: branch_name,
        cmk_version: cmk_version_rc_aware,
    );
}

return this;
