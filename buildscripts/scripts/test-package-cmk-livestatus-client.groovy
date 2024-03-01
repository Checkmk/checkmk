#!groovy

/// file: test-package-cmk-livestatus-client.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-livestatus-client') {
                sh("packages/cmk-livestatus-client/run --clean --all");
            }
        }
    }
}

return this;
