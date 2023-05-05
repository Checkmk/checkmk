#!groovy

/// file: test-shell-unit.groovy

def main() {

    def test_jenkins_helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside("--ulimit nofile=1024:1024 --init") {
            dir("${checkout_dir}") {
                test_jenkins_helper.execute_test([
                    name: "test-shell-unit",
                    cmd: "make -C tests test-unit-shell",
                    output_file: "shell-unit.txt"
                ]);

                test_jenkins_helper.analyse_issues("SHELLUNIT", "shell-unit.txt");
            }
        }
    }
}

return this;
