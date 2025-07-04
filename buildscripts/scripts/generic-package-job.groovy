#!groovy

/// file: generic-package-job.groovy

def secret_list(secret_vars) {
    return secret_vars ? secret_vars.split(' ') : [];
}

def validate_parameters() {
    if (COMMAND_LINE == "") {
        error("COMMAND_LINE parameter is empty - you need to specify a command to run.");
    }
}

def main() {
    check_job_parameters([
        "PACKAGE_PATH",
        "SECRET_VARS",
        "COMMAND_LINE",
        "DEPENDENCY_PATH_HASHES",
    ]);

    validate_parameters()

    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    currentBuild.description = "Running ${PACKAGE_PATH}<br>${currentBuild.description}";


    def output_file = PACKAGE_PATH.split("/")[-1] + ".log"
    dir(checkout_dir) {
        inside_container(init: true, privileged: true, set_docker_group_id: true) {
            withCredentials(secret_list(SECRET_VARS).collect { string(credentialsId: it, variable: it) }) {
                helper.execute_test([
                    name       : PACKAGE_PATH,
                    cmd        : "cd ${PACKAGE_PATH}; ${COMMAND_LINE}",
                    output_file: output_file,
                ]);
            }
            sh("mv ${PACKAGE_PATH}/${output_file} ${checkout_dir}");
        }
        archiveArtifacts(
            artifacts: "${output_file}",
            fingerprint: true,
        );
        setCustomBuildProperty(
            key: "path_hashes",
            value: directory_hashes(DEPENDENCY_PATH_HASHES.split(",").grep().collect {keyvalue -> keyvalue.split("=")[0]}),
        );
    }
}

return this;
