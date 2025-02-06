#!groovy

/// file: trigger-all-nightlies-fast.groovy

/// This job will trigger all other nightly build chains on a fixed node

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def all_editions = versioning.get_editions();
    def editions_to_test = all_editions;

    def job_parameters = [
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

    currentBuild.result = parallel(
        all_editions.collectEntries { edition ->
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
                        job: "${branch_base_folder}/trigger-cmk-build-chain-${edition}",
                        parameters: job_parameters,
                    );
                }
            }
        ]}
    );
}

return this;
