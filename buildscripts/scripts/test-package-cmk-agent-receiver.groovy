#!groovy

/// file: test-package-cmk-agent-receiver.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package cmk-agent-receiver') {
                sh("packages/cmk-agent-receiver/run --clean --all");
            }
        }
    }
}

return this;
