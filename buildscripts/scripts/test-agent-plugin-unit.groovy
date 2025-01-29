#!groovy

/// file: test-agent-plugin-unit.groovy

def get_agent_plugin_python_versions(String git_dir=".") {
    dir(git_dir) {
        def versions = (cmd_output("make --no-print-directory --file=defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS")
                ?: raise("Could not read AGENT_PLUGIN_PYTHON_VERSIONS from defines.make"));
        // Python 2.7 tests fail if they run in parallel with 3.x tests
        return versions.replace("2.7 ", "").split(" ");
    }
}

def main() {
    def python_versions = get_agent_plugin_python_versions(checkout_dir);

    inside_container(
        set_docker_group_id: true,
        priviliged: true,
    ) {
        dir("${checkout_dir}") {
            // pre-create virtual environments before parallel execution
            stage("prepare virtual environment") {
                sh("make .venv");
            }
            def test_builds = python_versions.collectEntries { python_version ->
                [(python_version) : {
                    stage("Test for python${python_version}") {
                        // Here we need the docker registry as we are using python:VERSION docker images
                        // which are stored on nexus.
                        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                            sh("make -C tests test-agent-plugin-unit-py${python_version}-docker");
                        }
                    }
                }]
            }
            parallel test_builds;

            // Python 2.7 tests fail if they run in parallel with 3.x tests
            stage("Test for python2.7") {
                // Here we need the docker registry as we are using python:VERSION docker images
                // which are stored on nexus.
                docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
                    sh("make -C tests test-agent-plugin-unit-py2.7-docker");
                }
            }
        }
    }
}

return this;
