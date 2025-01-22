#!groovy

/// file: test-python3-pylint.groovy

def main() {
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside('--ulimit nofile=1024:1024 --init') {
            stage('Run test-pylint') {
                dir("${checkout_dir}") {
                    sh("make -C tests test-pylint");
                }
            }
        }
    }
}

return this;
