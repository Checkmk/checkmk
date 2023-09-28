#!groovy

/// file: test-check-sql.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Compile & Test Check SQL') {
                sh("packages/check-sql/run --setup-environment --clean --all");
            }
        }
    }
}
return this;
