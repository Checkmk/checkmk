#!groovy

/// file: test-xss-crawl.groovy

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def testing_helper = load("${checkout_dir}/buildscripts/scripts/utils/integration.groovy");
    def safe_branch_name = versioning.safe_branch_name(scm);
    def version = "daily";

    check_job_parameters([
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
    ]);

    try {
        testing_helper.run_make_targets(
            DOCKER_GROUP_ID: get_docker_group_id(),
            DISTRO_LIST: ["ubuntu-20.04"],
            EDITION: "enterprise",
            VERSION: version,
            DOCKER_TAG: versioning.select_docker_tag(
                "", // 'build tag'
                "", // 'folder tag'
                safe_branch_name),  // 'branch' returns '<BRANCH>-latest'
            MAKE_TARGET: "test-xss-crawl-docker",
            BRANCH: safe_branch_name,
            cmk_version: versioning.get_cmk_version(safe_branch_name, version),
        );
    } finally {
        stage('archive crawler report') {
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

return this;
