#!groovy

/// file: test-sql-check.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Compile & Test SQL Check') {
                sh("packages/database_check/sql_check/run --setup-environment --clean --all");
            }
        }
    }
}
return this;
