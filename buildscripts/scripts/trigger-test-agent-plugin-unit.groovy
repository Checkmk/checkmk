#!groovy

/// file: trigger-test-agent-plugin-unit.groovy

String get_agent_plugin_python_versions() {
    return (cmd_output("make --no-print-directory --file=defines.make print-AGENT_PLUGIN_PYTHON_VERSIONS")
            ?: raise("Could not read AGENT_PLUGIN_PYTHON_VERSIONS from defines.make"));
}

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    def safe_branch_name = versioning.safe_branch_name();
    def python_versions = [];
    def branch_base_folder = package_helper.branch_base_folder(true);
    def relative_job_name = "${branch_base_folder}/builders/test-agent-plugin-unit";

    /// In order to ensure a fixed order for stages executed in parallel,
    /// we wait an increasing amount of time (N * 100ms).
    /// Without this we end up with a capped build overview matrix in the job view (Jenkins doesn't
    /// like changing order or amount of stages, which will happen with stages started `via parallel()`
    def timeOffsetForOrder = 0;

    stage("Preparation") {
        dir("${checkout_dir}") {
            inside_container_minimal(safe_branch_name: safe_branch_name) {
                python_versions = get_agent_plugin_python_versions().split(" ");
            }
        }
    }

    def test_stages = python_versions.collectEntries { python_version ->
        [("Python ${python_version}"): {
            sleep(0.1 * timeOffsetForOrder++);

            smart_stage(
                name: python_version,
                raiseOnError: false,
            ) {
                smart_build(
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: relative_job_name,
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        CIPARAM_OVERRIDE_DOCKER_TAG_BUILD: python_version,
                        // this is needed to re-use existing pod templates the smartest way
                        DISTRO: "python",
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    dest: checkout_dir,
                    no_remove_others: true, // do not delete other files in the dest dir
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(test_stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }

    stage("Concat artifacts") {
        dir("${checkout_dir}") {
            sh("""
                mkdir results
                cat agent-plugin-unit-junit-*.txt > results/agent-plugin-unit-junit.txt
            """);

            archiveArtifacts(
                artifacts: "results/agent-plugin-unit-junit.txt",
                fingerprint: true,
            );
        }
    }
}

return this;
