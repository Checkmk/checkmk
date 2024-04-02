#!groovy

/// file: test-package-check-http.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package check-http') {
                sh("packages/check-http/run --setup-environment --clean --all --features=reqwest/native-tls-vendored");
            }
        }
    }
}

return this;
