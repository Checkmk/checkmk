#!groovy

/// file: test-werks-package.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Validate .werks') {
                sh("scripts/run-pipenv run python -m cmk.werks.validate");
            }
        }
    }
}

return this;
