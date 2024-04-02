#!groovy

/// file: test-mk-sql.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Compile & Test mk-sql') {
                withCredentials([string(
                    credentialsId: "CI_TEST_SQL_DB_ENDPOINT",
                    variable:"CI_TEST_SQL_DB_ENDPOINT"
                )]) {
                    sh("packages/mk-sql/run --setup-environment --clean --all");
                }
            }
        }
    }
}

return this;
