#!groovy

/// file: test-package-package-cmk-frontend-vue.groovy

def main() {
    dir("${checkout_dir}") {
        docker_reference_image().inside() {
            stage('Test Package package-cmk-frontend-vue') {
                sh("packages/package-cmk-frontend-vue/run --clean --all");
            }
        }
    }
}

return this;
