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
                sh("""
                    set -o pipefail
                    PYTHON_VERSION_MAJ_MIN=${python_version} \
                        tests/agent-plugin-unit/bootstrap.sh --execute 2>&1 | tee ${output_file}
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
