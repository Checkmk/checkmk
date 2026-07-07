#!groovy

/// file: trigger-all-nightlies-fast.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

void main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(true);
    def safe_branch_name = versioning.safe_branch_name();

    def disable_cache = params.DISABLE_CACHE;
    def force_build = params.DISABLE_JENKINS_CACHE == true;
    def fake_artifacts = params.FAKE_ARTIFACTS;
    def override_editions = params.EDITIONS.trim() ?: "";

    def all_editions = [];
    def job_parameters = [
        CUSTOM_GIT_REF: effective_git_ref,
        FAKE_ARTIFACTS: fake_artifacts,
        DISABLE_CACHE: disable_cache,
    ];
    def job_parameters_no_check = [
        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
    ];

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        all_editions = versioning.get_editions();
    }
    def editions_to_test = all_editions;

    if (Calendar.getInstance().get(Calendar.HOUR_OF_DAY) in 12..15) {
        // build only "ultimate" edition on high noon or a little bit later
        editions_to_test = ["ultimatemt"];
    }

    if (override_editions) {
        editions_to_test = override_editions.replaceAll(',', ' ').split(' ').grep();
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |branch_base_folder:.... │${branch_base_folder}│
        |disable_cache:......... │${disable_cache}│
        |editions:.............. │${editions_to_test}│
        |fake_artifacts:........ │${fake_artifacts}│
        |fixed_node:............ |${params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE}|
        |force_build:........... │${force_build}│
        |job_parameters:........ │${job_parameters}│
        |job_parameters_no_check:│${job_parameters_no_check}│
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
                    force_build: force_build,
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
                force_build: force_build,
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
