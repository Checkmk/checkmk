#!groovy

/// file: test-package-cmk-graphing.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-graphing') {
                sh("packages/cmk-graphing/run --clean --all");
            }
        }
    }
}

return this;
