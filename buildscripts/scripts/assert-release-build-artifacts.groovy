#!groovy

// file: assert-release-build-artifacts.groovy

def main() {
    stage("Assert release build artifacts") {
        check_job_parameters([
            "VERSION_TO_CHECK",
        ])
        docker_image_from_alias("IMAGE_TESTING").inside("-v \$HOME/.cmk-credentials:\$HOME/.cmk-credentials -v /var/run/docker.sock:/var/run/docker.sock --group-add=${get_docker_group_id()}") {
            withEnv(["PYTHONUNBUFFERED=1"]) {
                dir("${checkout_dir}") {
                    sh(script: """scripts/run-pipenv run \
                    buildscripts/scripts/get_distros.py \
                    --editions_file "${checkout_dir}/editions.yml" \
                    assert_build_artifacts \
                    --version "${VERSION_TO_CHECK}" \
                    """);
                }
            }
        }
    }
}

return this;
