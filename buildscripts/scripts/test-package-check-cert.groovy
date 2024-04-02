#!groovy

/// file: test-package-check-cert.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package check-cert') {
                sh("packages/check-cert/run --setup-environment --clean --all --features=vendored");
            }
        }
    }
}

return this;
