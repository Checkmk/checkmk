#!groovy

/// file: test-package-check-http.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package check-http') {
                sh("packages/check-http/run --setup-environment --clean --all");
            }
        }
    }
}

return this;
