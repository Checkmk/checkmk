#!groovy

/// file: test-package-mk-sql.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
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
