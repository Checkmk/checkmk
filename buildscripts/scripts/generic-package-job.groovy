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
    currentBuild.description = "Running ${params.PACKAGE_PATH}<br>${currentBuild.description}";

    def output_file = params.PACKAGE_PATH.split("/")[-1] + ".log"
    dir(checkout_dir) {
        lock(label: "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}", quantity: 1, resource : null) {
            inside_container(init: true) {
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
