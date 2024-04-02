#!groovy

/// file: test-package-cmk-rulesets.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package cmk-rulesets') {
                sh("packages/cmk-rulesets/run --clean --all");
            }
        }
    }
}

return this;
