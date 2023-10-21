#!groovy

/// file: test-package-cmk-agent-based.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-agent-based') {
                sh("packages/cmk-agent-based/run --clean --all");
            }
        }
    }
}

return this;
