#!groovy

/// file: trigger-packages.groovy

def main() {
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
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: false);
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
            def stepName = "${p.name}";
            def build_instance = null;

            smart_stage(
                name: stepName,
                raiseOnError: false,
            ) {
                build_instance = smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/build-cmk-package",
                    force_build: params.FORCE_BUILD,
                    dependency_paths: [p.path] + p.dependencies,
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        PACKAGE_PATH:  p.path,
                        SECRET_VARS: p.sec_vars.join(","),
                        COMMAND_LINE: p.command_line,
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
                        notify.notify_maintainer_of_package(p.maintainers, stepName, "${build_instance.absoluteUrl}" + "console")
                    }
                    throw new Exception("Job ${stepName} failed");
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

return this
