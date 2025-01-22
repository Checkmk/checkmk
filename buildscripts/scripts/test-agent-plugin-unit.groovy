#!groovy

/// file: test-agent-plugin-unit.groovy

def get_agent_plugin_python_versions(String git_dir=".") {
    dir(git_dir) {
        def versions = (cmd_output("make --no-print-directory --file=defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS")
                ?: raise("Could not read AGENT_PLUGIN_PYTHON_VERSIONS from defines.make"));
        return versions.split(" ")
    }
}


def main() {
    def python_versions = get_agent_plugin_python_versions(checkout_dir);

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
                    [(python_version) : {
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
