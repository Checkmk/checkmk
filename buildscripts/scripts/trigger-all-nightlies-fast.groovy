#!groovy

/// file: trigger-all-nightlies-fast.groovy

/// This job will trigger all other nightly build chains on a fixed node

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/";
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def all_editions = versioning.get_editions();
    def editions_to_test = all_editions;

    def job_parameters = [
        [$class: 'StringParameterValue',  name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE],
        [$class: 'StringParameterValue',  name: 'CUSTOM_GIT_REF', value: params.CUSTOM_GIT_REF],
    ];

    def override_editions = params.EDITIONS.trim() ?: "";
    if (override_editions) {
        editions_to_test = override_editions.replaceAll(',', ' ').split(' ').grep();
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |editions:.............. │${editions_to_test}│
        |base_folder:........... │${base_folder}│
        |job_parameters:........ │${job_parameters}│
        |fixed_node:............ |${params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE}|
        |===================================================
        """.stripMargin());

    def build_for_parallel = [:];
    all_editions.each { item ->
        def edition = item;
        def stepName = "Trigger ${edition}";

        build_for_parallel[stepName] = { ->
            def run_condition = edition in editions_to_test;
            println("Should ${edition} be triggered? ${run_condition}");

            /// this makes sure the whole parallel thread is marked as skipped
            if (! run_condition){
                Utils.markStageSkippedForConditional(stepName);
            }

            smart_stage(
                name: stepName,
                condition: run_condition,
                raiseOnError: true,
            ) {
                print(
                    """
                    |===== CONFIGURATION ===============================
                    |this_job_parameters:... │${this_job_parameters}│
                    |===================================================
                    """.stripMargin());
                build(
                    job: "${base_folder}/trigger-cmk-build-chain-${edition}",
                    propagate: true,  // Raise any errors
                    parameters: this_job_parameters,
                );
            }
        }
    }

    stage('Run trigger all nightlies') {
        parallel build_for_parallel;
    }
}

return this;
