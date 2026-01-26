#!groovy

/// file: trigger-packages.groovy

void main() {
    check_job_parameters([
        "FORCE_BUILD",
    ]);

    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def results_dir = "results";
    def packages_file = "${results_dir}/packages_generated.json";
    def packages = "";
    def branch_base_folder = package_helper.branch_base_folder(false);
    def send_notification_mail = !currentBuild.fullProjectName.contains("/cv/");

    stage("Preparation") {
        dir("${checkout_dir}") {
            inside_container_minimal(safe_branch_name: safe_branch_name) {
                sh("rm -rf results; mkdir results");
                sh("buildscripts/scripts/collect_packages.py packages non-free/packages > ${packages_file}");
                packages = load_json(packages_file);
            }
        }
    }

    def test_stages = packages.collectEntries { p ->
        [("${p.name}"): {
            def relative_job_name = "${branch_base_folder}/builders/build-cmk-package";
            if (env.USE_K8S_GENERIC_PACKAGES == "1") {
                relative_job_name = "${relative_job_name}-k8s";
            }
            def stepName = "${p.name}";
            def build_instance = null;
            // to be fixed with CMK-29585
            if (p.path in ["non-free/packages/cmk-relay-engine", "packages/cmk-agent-receiver"]) {
                relative_job_name = relative_job_name.split("-k8s")[0];
            }

            smart_stage(
                name: stepName,
                raiseOnError: false,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: relative_job_name,
                    force_build: params.FORCE_BUILD,
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        PACKAGE_PATH:  p.path,
                        SECRET_VARS: p.sec_vars.join(","),
                        COMMAND_LINE: p.command_line,
                        DISTRO: "REFERENCE_IMAGE",
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );

                if ("${build_instance.result}" != "SUCCESS") {
                    if (send_notification_mail) {
                        notify.notify_maintainer_of_package(p.maintainers, stepName, "${build_instance.absoluteUrl}" + "console");
                    }
                    fail("Job ${stepName} failed");
                }
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Archive stuff") {
        show_duration("archiveArtifacts") {
            archiveArtifacts(allowEmptyArchive: true, artifacts: 'results/*');
        }
    }
}

return this;
