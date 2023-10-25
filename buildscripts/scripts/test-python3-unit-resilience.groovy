#!groovy

/// file: test-python3-unit-resilience.groovy

def main() {
    def docker_args = "--ulimit nofile=1024:1024 --init";
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            stage('run test-unit-resilience') {
                dir("${checkout_dir}") {
                    try {
                        sh("make -C tests test-unit-resilience");
                    }
                    catch(Exception e) {
                        // We want to keep failed resilience builds in order to follow a process, see CMK-14487
                        currentBuild.setKeepLog(true)
                        throw e
                    }
                }
            }
        }
    }
}

return this;
