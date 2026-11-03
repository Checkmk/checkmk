#!groovy

/// file: generic-package-job.groovy

static ArrayList secret_list(String secret_vars) {
    return secret_vars ? secret_vars.split(' ') : [];
}

void validate_parameters() {
    if (params.COMMAND_LINE == "") {
        error("COMMAND_LINE parameter is empty - you need to specify a command to run.");
    }
}

void main() {
    check_job_parameters([
        "COMMAND_LINE",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISTRO",
        "PACKAGE_PATH",
        "SECRET_VARS",
    ]);

    validate_parameters();

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def output_file = params.PACKAGE_PATH.split("/")[-1] + ".txt";

    currentBuild.description = "Running ${params.PACKAGE_PATH}<br>${currentBuild.description}";

    dir(checkout_dir) {
        this_call_site(safe_branch_name, output_file);

        // Can be removed once ci-artifacts doesn't fail anymore on empty files
        def is_empty = sh(script:"[[ -s ${output_file} ]]", returnStatus:true);
        def artifacts = "${params.FILE_ARCHIVING_PATTERN}" + (is_empty ? "" : ", ${output_file}");

        archiveArtifacts(
            artifacts: artifacts,
            fingerprint: true,
        );
    }
}

void this_call_site(String safe_branch_name, String output_file) {
    def helper = load("${checkout_dir}/buildscripts/scripts/utils/test_helper.groovy");

    // fancy fancy hack, see buildscripts/scripts/utils/docker_image_aliases_helper.groovy why
    def container_name = "testing-ubuntu-2204-checkmk-${safe_branch_name.replace('.', '-')}";
    withCredentials(secret_list(params.SECRET_VARS).collect {
        string(credentialsId: it, variable: it)
    }) {
        helper.execute_test([
            name       : params.PACKAGE_PATH,
            cmd        : "cd ${params.PACKAGE_PATH}; ${params.COMMAND_LINE}",
            output_file: output_file,
            container_name: container_name,
        ]);
    }
    sh("mv ${params.PACKAGE_PATH}/${output_file} ${checkout_dir}");
}

return this;
