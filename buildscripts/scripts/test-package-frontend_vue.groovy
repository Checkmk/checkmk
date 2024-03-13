#!groovy

/// file: test-package-package-cmk-frontend-vue.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package package-cmk-frontend-vue') {
                sh("packages/package-cmk-frontend-vue/run --clean --all");
            }
        }
    }
}

return this;
