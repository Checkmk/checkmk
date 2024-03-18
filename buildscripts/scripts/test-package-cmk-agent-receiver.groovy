#!groovy

/// file: test-package-cmk-agent-receiver.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-agent-receiver') {
                sh("packages/cmk-agent-receiver/run --clean --all");
            }
        }
    }
}

return this;
