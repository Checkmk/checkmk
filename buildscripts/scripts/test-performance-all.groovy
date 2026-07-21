#!groovy

/// file: test-performance-all.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    // The branch-specific part must not contain dots (e.g. 2.5.0),
    // because this results in an invalid branch name.
    // The pod templates uses - instead.
    def container_safe_branch_name = safe_branch_name.replace(".", "-");

    def make_target = "test-performance-all";
    def result_dir = "results";

    dir("${checkout_dir}") {
        stage("Prepare workspace") {
            sh("""
                rm -rf ${result_dir}
                mkdir -p ${result_dir}
            """);
        }

        // Unlike test-performance, the Bazel-based suites need no Checkmk
        // package and no site: they run self-contained against their own
        // backends (e.g. a standalone ClickHouse from @clickhouse), so they
        // run directly in a k8s pod like the unit and component tests.
        test_jenkins_helper.execute_test([
            name: make_target,
            cmd: "RESULT_PATH='${checkout_dir}/${result_dir}' tests/run_tests.sh ${make_target}",
            container_name: "ubuntu-2404-${container_safe_branch_name}-latest",

            creds_files: [
                [credentialsId: "QA_POSTGRES_KEY_FILE", location: "${checkout_dir}/QA_POSTGRES_KEY",],
                [credentialsId: "QA_POSTGRES_CERT_FILE", location: "${checkout_dir}/QA_POSTGRES_CERT",],
                [credentialsId: "QA_ROOT_CERT_FILE", location: "${checkout_dir}/QA_ROOT_CERT",],
            ],
            cred_env: [
                string(credentialsId: 'JIRA_API_TOKEN_QA_ALERTS', variable: 'QA_JIRA_API_TOKEN'),
            ],
        ]);

        stage("Archive / process test reports") {
            dir("${checkout_dir}/${result_dir}") {
                show_duration("archiveArtifacts") {
                    archiveArtifacts(
                        artifacts: "**",
                        fingerprint: true,
                    );
                }
                xunit([Custom(
                    customXSL: "${checkout_dir}/buildscripts/scripts/schema/pytest-xunit.xsl",
                    deleteOutputFiles: true,
                    failIfNotNew: true,
                    pattern: "**/junit.xml",
                    skipNoTestFiles: false,
                    stopProcessingIfError: true
                )]);
            }
        }
    }
}

return this;
