#!groovy

/// file: trigger-all-nightlies-fast.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def all_editions = versioning.get_editions();
    def editions_to_test = all_editions;

    if (Calendar.getInstance().get(Calendar.HOUR_OF_DAY) in 12..15) {
        // build only "ultimate" edition on high noon or a little bit later
        editions_to_test = ["ultimatemt"];
    }

    def job_parameters = [
        CUSTOM_GIT_REF: effective_git_ref,
    ];
    def job_parameters_no_check = [
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
    ];

    def override_editions = params.EDITIONS.trim() ?: "";
    if (override_editions) {
        editions_to_test = override_editions.replaceAll(',', ' ').split(' ').grep();
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |editions:.............. │${editions_to_test}│
        |branch_base_folder:.... │${branch_base_folder}│
        |job_parameters:........ │${job_parameters}│
        |job_parameters_no_check:│${job_parameters_no_check}│
        |fixed_node:............ |${params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE}|
        |safe_branch_name:...... │${safe_branch_name}│
        |===================================================
        """.stripMargin());

    def stages = all_editions.collectEntries { edition ->
        [("${edition}") : {
            def stepName = "Trigger ${edition}";
            def run_condition = edition in editions_to_test;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition) {
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: true,
            ) {
                smart_build(
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/trigger-cmk-build-chain-${edition}",
                    build_params: job_parameters,
                    build_params_no_check: job_parameters_no_check,
                    download: false,
                );
            }
        }]
    }

    stages["build-relay-image"] = {
        smart_stage(
            name: "Trigger Relay Image Build",
            raiseOnError: true,
        ) {
            smart_build(
                use_upstream_build: true,
                relative_job_name: "${branch_base_folder}/builders/build-cmk-relay-image",
                build_params: job_parameters,
                build_params_no_check: job_parameters_no_check,
                download: false,
            );
        }
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
