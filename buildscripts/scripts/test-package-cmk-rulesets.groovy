#!groovy

/// file: test-package-cmk-rulesets.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-rulesets') {
                sh("packages/cmk-rulesets/run --clean --all");
            }
        }
    }
}

return this;
