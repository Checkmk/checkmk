#!groovy

/// file: test-package-cmk-server-side-calls.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-server-side-calls') {
                sh("packages/cmk-server-side-calls/run --clean --all");
            }
        }
    }
}

return this;
