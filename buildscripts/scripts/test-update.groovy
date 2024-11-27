#!groovy

/// file: test-update.groovy

def build_make_target(edition, cross_edition_target="") {
    def prefix = "test-update-";
    def suffix = "-docker";
    switch(edition) {
        case 'enterprise':
            switch(cross_edition_target) {
                case 'cce':
                case 'cme':
                    // from CEE to CCE or CME
                    return prefix + "cross-edition-" + cross_edition_target + suffix;
                default:
                    return prefix + "cee" + suffix;
            }
        case 'cloud':
            return prefix + "cce" + suffix;
        case 'saas':
            return prefix + "cse" + suffix;
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
        "CROSS_EDITION_TARGET",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");

    def safe_branch_name = versioning.safe_branch_name(scm);
    def branch_version = versioning.get_branch_version(checkout_dir);
    // When building from a git tag (VERSION != "daily"), we cannot get the branch name from the scm so used defines.make instead.
    // this is save on master as there are no tags/versions built other than daily
    def branch_name = (params.VERSION == "daily") ? safe_branch_name : branch_version;
    def cmk_version_rc_aware = versioning.get_cmk_version(safe_branch_name, branch_version, params.VERSION);
    def cmk_version = versioning.strip_rc_number_from_version(cmk_version_rc_aware);

    def edition = params.EDITION;
    def distros = versioning.get_distros(edition: edition, use_case: "daily_update_tests", override: OVERRIDE_DISTROS);
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def cross_edition_target = env.CROSS_EDITION_TARGET ?: "";
    if (cross_edition_target) {
        // see CMK-18366
        distros = ["ubuntu-22.04"];
    }
    def make_target = build_make_target(EDITION, cross_edition_target);

    print(
        """
        |===== CONFIGURATION ===============================
        |distros:.................. │${distros}│
        |edition:.................. │${edition}│
        |branch_name:.............. │${branch_name}│
        |safe_branch_name:......... │${safe_branch_name}│
        |cmk_version:.............. │${cmk_version}│
        |cmk_version_rc_aware:..... │${cmk_version_rc_aware}│
        |branch_version:........... │${branch_version}│
        |docker_tag:............... │${docker_tag}│
        |cross_edition_target:..... |${cross_edition_target}|
        |checkout_dir:............. │${checkout_dir}│
        |make_target:.............. |${make_target}|
        |===================================================
        """.stripMargin());

    stage("Run `make ${make_target}`") {
        docker.withRegistry(DOCKER_REGISTRY, "nexus") {
            testing_helper.run_make_targets(
                DOCKER_GROUP_ID: get_docker_group_id(),
                DISTRO_LIST: distros,
                EDITION: edition,
                VERSION: VERSION,
                DOCKER_TAG: docker_tag,
                MAKE_TARGET: make_target,
                BRANCH: branch_name,
                cmk_version: cmk_version_rc_aware,
                OTEL_EXPORTER_OTLP_ENDPOINT: "",
            );
        }
    }
}

return this;
