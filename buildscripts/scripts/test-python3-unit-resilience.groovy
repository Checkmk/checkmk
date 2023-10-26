#!groovy

/// file: test-python3-unit-resilience.groovy

def main() {
    def docker_args = "--ulimit nofile=1024:1024 --init";
    def relative_result_path = "results/junit-resilience.xml"
    def result_path = "${checkout_dir}/${relative_result_path}";
    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            stage('run test-unit-resilience') {
                dir("${checkout_dir}") {
                    try {
                        withEnv([
                            "PYTEST_ADDOPTS='--junitxml=${result_path}'",
                        ]) {
                            sh("make -C tests test-unit-resilience");
                        }
                    } catch(Exception e) {
                        // We want to keep failed resilience builds in order to follow a process, see CMK-14487
                        currentBuild.setKeepLog(true)
                        throw e
                    } finally {
                        step([
                            $class: "JUnitResultArchiver",
                            // Absolutley no idea why I cannot use an absolute path here...
                            testResults: "${relative_result_path}",
                        ])
                    }
                }
            }
        }
    }
}

return this;
