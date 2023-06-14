#!groovy

/// file: test-python3-unit-slow.groovy

def main() {
    def docker_args = "--ulimit nofile=1024:1024 --init";
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            stage('run test-unit-slow') {
                dir("${checkout_dir}") {
                    sh("make -C tests test-unit-slow");
                }
            }
        }
    }
}

return this;
