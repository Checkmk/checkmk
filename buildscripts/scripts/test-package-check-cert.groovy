#!groovy

/// file: test-package-check-cert.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package check-cert') {
                sh("packages/check-cert/run --setup-environment --clean --all");
            }
        }
    }
}

return this;
