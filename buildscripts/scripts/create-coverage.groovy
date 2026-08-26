#!groovy

/// file: create-coverage.groovy

void main() {
    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def container_safe_branch_name = safe_branch_name.replace(".", "-");
    def container_name = "ubuntu-2404-${container_safe_branch_name}-latest";

    dir("${checkout_dir}") {
        withCredentials([
            string(credentialsId: "CI_TEST_SQL_DB_ENDPOINT", variable: "CI_TEST_SQL_DB_ENDPOINT"),
            usernamePassword(
                credentialsId: 'qa-kpi-metabase-postgres',
                usernameVariable: 'QA_POSTGRES_USER',
                passwordVariable: 'QA_POSTGRES_PASSWORD'
            ),
        ]) {
            test_jenkins_helper.execute_test([
                name: "create-coverage",
                cmd: """\
export POSTGRES_HOST="dev-kpi.lan.checkmk.net"
export POSTGRES_PORT=5432
export POSTGRES_DB=metabase
tests/qa_metrics/test_coverage/main.sh --run --generate-html --upload-totals --upload-per-module""",
                container_name: container_name,
                disable_hot_cache: true,
            ]);
        }

        smart_stage(
            name: "Deploy HTML report",
            // only run if previous stages were successful
            condition: currentBuild.result == null,
            raiseOnError: true,
        ) {
            container(container_name) {
                withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
                    sh("""
                        scp -r -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} \
                        results/test_coverage/repository/html/* ${DEV_DOCS_URL}/test_coverage
                    """);
                }
            }
        }
    }
}

return this;
