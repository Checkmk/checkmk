#!groovy

/// file: test-agent-plugin-unit.groovy

String get_agent_plugin_python_versions(String git_dir=".") {
    dir(git_dir) {
        return (cmd_output("make --no-print-directory --file=defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS_DOCKER")
                ?: raise("Could not read AGENT_PLUGIN_PYTHON_VERSIONS_DOCKER from defines.make")).split(" ");
    }
}

void main() {
    def python_versions = get_agent_plugin_python_versions(checkout_dir);

    inside_container(
        set_docker_group_id: true,
        privileged: true,
    ) {
        dir("${checkout_dir}") {
            // TODO: Drop the make target as soon as we drop the compatibilty to python < 3.8
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
            parallel(test_builds);

            stage("Test for remaining python versions") {
                sh("bazel test //tests/agent-plugin-unit:supported_python_versions");
            }
        }
    }
}

return this;
