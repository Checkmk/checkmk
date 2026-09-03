#!groovy

/// file: generic-package-job.groovy

def secret_list(secret_vars) {
    return secret_vars ? secret_vars.split(',') : [];
}

def validate_parameters() {
    if (params.COMMAND_LINE == "") {
        error("COMMAND_LINE parameter is empty - you need to specify a command to run.");
    }
}

def main() {
    check_job_parameters([
        "PACKAGE_PATH",
        "SECRET_VARS",
        "COMMAND_LINE",
    ]);

    validate_parameters();

    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();

    currentBuild.description = "Running ${params.PACKAGE_PATH}<br>${currentBuild.description}";

    def output_file = params.PACKAGE_PATH.split("/")[-1] + ".log"

    def container_name = "testing-ubuntu-22.04-checkmk-${safe_branch_name}";
    def docker_tag = "latest-with-docker";
    // testing-ubuntu-22.04-checkmk-2.4.0:latest-with-docker

    dir(checkout_dir) {
        lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
            inside_container(
                image: docker.image("${docker_registry_no_http}/${container_name}:${docker_tag}"),
                pull: true,
                init: true,
            ) {
                withCredentials(secret_list(params.SECRET_VARS).collect { string(credentialsId: it, variable: it) }) {
                    helper.execute_test([
                        name       : params.PACKAGE_PATH,
                        cmd        : "cd ${params.PACKAGE_PATH}; ${params.COMMAND_LINE}",
                        output_file: output_file,
                    ]);
                }
                sh("mv ${params.PACKAGE_PATH}/${output_file} ${checkout_dir}");
            }
        }

        archiveArtifacts(
            artifacts: "${output_file}",
            fingerprint: true,
        );
    }
}

return this;
