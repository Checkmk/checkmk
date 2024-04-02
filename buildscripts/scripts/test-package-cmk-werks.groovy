#!groovy

/// file: test-werks-package.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
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
