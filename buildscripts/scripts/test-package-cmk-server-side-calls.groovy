#!groovy

/// file: test-package-cmk-server-side-calls.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package cmk-server-side-calls') {
                sh("packages/cmk-server-side-calls/run --clean --all");
            }
        }
    }
}

return this;
