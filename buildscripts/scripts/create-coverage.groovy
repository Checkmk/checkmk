#!groovy

/// file: create-coverage.groovy

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def container_safe_branch_name = safe_branch_name.replace(".", "-");
    def container_name = "ubuntu-2404-${container_safe_branch_name}-latest";

    // Deliberately not using test_helper.execute_test: it swallows the error, so a failing run
    // would neither abort the job nor trigger the failure notification.
    dir("${checkout_dir}") {
        stage("Run create-coverage") {
            container(container_name) {
                withCredentials([
                    string(credentialsId: "CI_TEST_SQL_DB_ENDPOINT", variable: "CI_TEST_SQL_DB_ENDPOINT"),
                    usernamePassword(
                        credentialsId: 'qa-kpi-metabase-postgres',
                        usernameVariable: 'QA_POSTGRES_USER',
                        passwordVariable: 'QA_POSTGRES_PASSWORD'
                    ),
                ]) {
                    sh("""
                        export POSTGRES_HOST="dev-kpi.lan.checkmk.net"
                        export POSTGRES_PORT=5432
                        export POSTGRES_DB=metabase
                        tests/qa_metrics/test_coverage/repository.sh --run --generate-html --upload-totals --upload-per-module
                    """);
                }
            }
        }

        stage("Deploy HTML report") {
            container(container_name) {
                withCredentials([file(credentialsId: 'Release_Key', variable: 'RELEASE_KEY')]) {
                    // html/. instead of html/*: the glob skips dot-prefixed .ide folders
                    sh("""
                        scp -r -o StrictHostKeyChecking=accept-new -i ${RELEASE_KEY} \
                        results/test_coverage/repository/html/. ${DEV_DOCS_URL}/test_coverage
                    """);
                }
            }
        }
    }
}

return this;
