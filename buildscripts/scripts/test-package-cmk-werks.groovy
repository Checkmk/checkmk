#!groovy

/// file: test-package-cmk-werks.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package cmk-werks') {
                sh("packages/cmk-werks/run --clean --all");
            }

            stage('Validate .werks') {
                sh("scripts/run-pipenv run python -m cmk.werks.validate");
            }
        }
    }
}

return this;
