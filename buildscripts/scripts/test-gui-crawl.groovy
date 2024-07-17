#!groovy

/// file: test-gui-crawl.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def safe_branch_name = versioning.safe_branch_name(scm);
    def cmk_version = versioning.get_cmk_version(safe_branch_name, "daily");
    def docker_group_id = get_docker_group_id();
    def docker_tag = versioning.select_docker_tag(
        "",                // 'build tag'
        safe_branch_name,  // 'branch'
    )

    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    try {
        testing_helper.run_make_targets(
            DOCKER_GROUP_ID: docker_group_id,
            DISTRO_LIST: ["ubuntu-20.04"],
            EDITION: "enterprise",
            VERSION: "git",
            DOCKER_TAG: docker_tag,
            MAKE_TARGET: "test-gui-crawl-docker",
            BRANCH: safe_branch_name,
            cmk_version: cmk_version,
        )
    } finally {
        stage('archive crawler report') {
            dir("${WORKSPACE}") {
                xunit([
                    JUnit(
                    deleteOutputFiles: true,
                    failIfNotNew: true,
                    pattern: "**/crawl.xml",
                    skipNoTestFiles: false,
                    stopProcessingIfError: true
                    )
                ])
            }
        }
    }
}

return this;
