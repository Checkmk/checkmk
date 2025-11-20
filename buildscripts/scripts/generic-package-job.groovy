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
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISTRO",
    ]);

    validate_parameters();

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");
    currentBuild.description = "Running ${PACKAGE_PATH}<br>${currentBuild.description}";

    def distro = DISTRO;

    def safe_branch_name = versioning.safe_branch_name();
    def docker_tag = versioning.select_docker_tag(
        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def output_file = PACKAGE_PATH.split("/")[-1] + ".log"

    def inside_container_args = [
        init: true,
        privileged: true,
        pull: true,
        set_docker_group_id: true,
    ]

    if (distro != "REFERENCE_IMAGE") {
        inside_container_args += [
            image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}")
        ]
    }

    dir(checkout_dir) {
        inside_container(inside_container_args) {
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
            artifacts: "${output_file}, ${FILE_ARCHIVING_PATTERN}",
            fingerprint: true,
        );
}
}

return this;
