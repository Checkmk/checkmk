def main() {
    // Due to https://github.com/pypa/pypi-support/issues/978, we need to disable Plugin tests for py2.6
    // until we have a feasible solution or we drop the support for 2.6 completly.
    def python_versions = ["2.7", "3.4", "3.5", "3.6", "3.7", "3.8", "3.9"];

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def docker_args = "-v /var/run/docker.sock:/var/run/docker.sock --group-add=${get_docker_group_id()}";

    docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
        docker_image_from_alias("IMAGE_TESTING").inside(docker_args) {
            dir("${checkout_dir}") {
                // pre-create virtual environments before parallel execution
                stage("prepare virtual environment") {
                    sh("make .venv");
                }
                def test_builds = python_versions.collectEntries { python_version ->
                    [python_version : {
                        stage("Test for python${python_version}") {
                            sh("make -C tests test-agent-plugin-unit-py${python_version}-docker");
                        }
                    }]
                }
                parallel test_builds;
            }
        }
    }
}
return this;
