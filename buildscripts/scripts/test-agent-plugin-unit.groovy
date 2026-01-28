#!groovy

/// file: test-agent-plugin-unit.groovy

void main() {
    def python_version = params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD;
    def distro = params.DISTRO;
    def output_file = "agent-plugin-unit-junit-${python_version}.txt";

    dir("${checkout_dir}") {
        stage("Test for python${python_version}") {
            inside_container(
                image: docker.image("${docker_registry_no_http}/${distro}:${python_version}"),
                pull: true,
            ) {
                def pymongo_version = "";
                // see Change-Id Ifae494bec4849ef7bd34348f8977310fb64b00e5
                if (python_version == "3.4") {
                    pymongo_version = "==3.12";
                }

                // the full list of python packages is based on Change-Id Ia88498098c77bf9199cf5ab9d8fb4d1e84133492
                sh("""
                    python --version

                    # taken from "check_mk/tests/agent-plugin-unit/Dockerfile"
                    python${python_version} -m pip \
                        install pytest pytest-mock mock requests "pymongo${pymongo_version}" \
                        --target \$(python${python_version} -c 'import sys; print(sys.path[-1])')

                    mkdir /tests /tests/datasets /agents
                    cp -r tests/agent-plugin-unit/datasets/* /tests/datasets/
                    cp -r agents/ /agents/
                    find tests/agent-plugin-unit/ -maxdepth 1 -type f -exec cp {} /tests/ \\;

                    python${python_version} -m pytest "/tests" 2>&1 | tee ${output_file}
                """);

                archiveArtifacts(
                    artifacts: "${output_file}",
                    fingerprint: true,
                );
            }
        }
    }
}

return this;
