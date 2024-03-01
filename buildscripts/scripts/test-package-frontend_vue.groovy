#!groovy

/// file: test-package-package-frontend_vue.groovy

def main() {
    dir("${checkout_dir}") {
        docker_image_from_alias("IMAGE_TESTING").inside() {
            stage('Test Package package-frontend_vue') {
                sh("packages/package-frontend_vue/run --clean --all");
            }
        }
    }
}

return this;
