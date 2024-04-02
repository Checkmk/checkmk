#!groovy

/// file: test-package-cmk-graphing.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package cmk-graphing') {
                sh("packages/cmk-graphing/run --clean --all");
            }
        }
    }
}

return this;
