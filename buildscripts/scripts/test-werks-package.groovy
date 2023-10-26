#!groovy

/// file: test-werks-package.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test werk package') {
                sh("packages/cmk-werks/run");
            }
        }
    }
}

return this;
