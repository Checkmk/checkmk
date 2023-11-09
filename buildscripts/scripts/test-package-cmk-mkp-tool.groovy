#!groovy

/// file: test-package-cmk-mkp-tool.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-mkp-tool') {
                sh("packages/cmk-mkp-tool/run --clean --all");
            }
        }
    }
}

return this;
