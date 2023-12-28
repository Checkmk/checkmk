#!groovy

/// file: test-python3-code-quality.groovy

def main() {
    def docker_args = "--ulimit nofile=1024:1024 --init";
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            stage('test python3 code quality') {
                dir("${checkout_dir}") {
                    sh("make -C tests test-code-quality");
                }
            }
        }
    }
}

return this;
