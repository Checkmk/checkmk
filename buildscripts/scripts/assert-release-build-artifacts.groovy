#!groovy

// file: assert-release-build-artifacts.groovy

def main() {
    stage("Assert release build artifacts") {
        check_job_parameters([
            "VERSION_TO_CHECK",
        ])
        inside_container(
            set_docker_group_id: true,
            mount_credentials: true,
            priviliged: true,
        ) {
            withCredentials([
                usernamePassword(
                    credentialsId: 'nexus',
                    passwordVariable: 'NEXUS_PASSWORD',
                    usernameVariable: 'NEXUS_USER')]) {
                withEnv(["PYTHONUNBUFFERED=1"]) {
                    dir("${checkout_dir}") {
                        sh(script: """scripts/run-pipenv run \
                        buildscripts/scripts/assert_build_artifacts.py \
                        --editions_file "${checkout_dir}/editions.yml" \
                        assert_build_artifacts \
                        --version "${VERSION_TO_CHECK}" \
                        """);
                    }
                }
            }
        }
    }
}

return this;
