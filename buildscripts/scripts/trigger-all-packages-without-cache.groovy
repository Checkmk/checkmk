#!groovy

/// file: trigger-all-packages-without-cache.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def all_editions = versioning.get_editions();
    def editions_to_test = all_editions;

    def job_parameters = [
        booleanParam(name: "DISABLE_CACHE", value: true),
        stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE),
        stringParam(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
        stringParam(name: "CIPARAM_BISECT_COMMENT", value: params.CIPARAM_BISECT_COMMENT),
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
        |fixed_node:............ |${params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE}|
        |===================================================
        """.stripMargin());

    def stages = all_editions.collectEntries { edition ->
        [("${edition}") : {
            def stepName = "Trigger ${edition}";
            def run_condition = edition in editions_to_test;

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: true,
            ) {
                smart_build(
                    job: "${branch_base_folder}/nightly-${edition}/build-cmk-deliverables-no-cache",
                    parameters: job_parameters,
                );
            }
        }]
    }
    currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;
