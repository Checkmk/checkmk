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
        "PACKAGE_PATH",
        "SECRET_VARS",
        "COMMAND_LINE",
        "CIPARAM_OVERRIDE_DOCKER_TAG_BUILD",
        "DISTRO",
    ]);

    validate_parameters();

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    currentBuild.description = "Running ${params.PACKAGE_PATH}<br>${currentBuild.description}";

    def distro = params.DISTRO;

    def safe_branch_name = versioning.safe_branch_name();
    def docker_tag = versioning.select_docker_tag(
        params.CIPARAM_OVERRIDE_DOCKER_TAG_BUILD,  // 'build tag'
        safe_branch_name,                   // 'branch' returns '<BRANCH>-latest'
    );

    def output_file = params.PACKAGE_PATH.split("/")[-1] + ".log";

    def inside_container_args = [
        init: true,
        privileged: true,
        pull: true,
        set_docker_group_id: true,
    ];

    if (distro != "REFERENCE_IMAGE") {
        inside_container_args += [
            image: docker.image("${docker_registry_no_http}/${distro}:${docker_tag}")
        ]
    }

    dir(checkout_dir) {
        // to be fixed with CMK-29585
        if ((params.PACKAGE_PATH in ["non-free/packages/cmk-relay-engine", "packages/cmk-agent-receiver"]) ||
            (params.PACKAGE_PATH == "packages/mk-oracle" && distro == "almalinux-8")) {
            inside_container(inside_container_args) {
                this_call_site(safe_branch_name, output_file);
            }
        } else {
            this_call_site(safe_branch_name, output_file);
            }

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

    def lock_label = "bzl_lock_${env.NODE_NAME.split('\\.')[0].split('-')[-1]}";
    if (kubernetes_inherit_from != "UNSET") {
        lock_label = "bzl_lock_k8s";
    }
    lock(label: lock_label, quantity: 1, resource : null) {
        withCredentials(secret_list(params.SECRET_VARS).collect {
            string(credentialsId: it, variable: it)
        }) {
            helper.execute_test([
                name       : params.PACKAGE_PATH,
                cmd        : "cd ${params.PACKAGE_PATH}; ${params.COMMAND_LINE}",
                output_file: output_file,
                container_name: "testing-ubuntu-2204-checkmk-${safe_branch_name}",
            ]);
        }
        sh("mv ${params.PACKAGE_PATH}/${output_file} ${checkout_dir}");
    }
}

return this;
