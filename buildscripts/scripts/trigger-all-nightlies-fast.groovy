#!groovy

/// file: trigger-all-nightlies-fast.groovy

/// This job will trigger all other nightly build chains on a fixed node

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/";
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def all_editions = versioning.get_editions();
    def editions_to_test = all_editions;

    if (Calendar.getInstance().get(Calendar.HOUR_OF_DAY) in 12..15) {
        // build only enterprise on high noon or a little bit later
        editions_to_test = ["enterprise"];
    }

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
    def parallel_stages_states = [];

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
                raiseOnError: false,
            ) {
                def this_exit_successfully = false;
                def this_job_parameters = job_parameters + [$class: 'StringParameterValue', name: 'EDITION', value: edition];
                print(
                    """
                    |===== CONFIGURATION ===============================
                    |this_job_parameters:... │${this_job_parameters}│
                    |===================================================
                    """.stripMargin());
                def job = build(
                    job: "${base_folder}/trigger-cmk-build-chain-${edition}",
                    propagate: false,   // do not raise here, continue, get status via result property later
                    parameters: this_job_parameters,
                );
                println("job result is: ${job.result}");
                // be really really sure if it is a success
                if (job.result == "SUCCESS") {
                    this_exit_successfully = true;
                } else {
                    error("${edition} failed");
                }
                parallel_stages_states.add(this_exit_successfully);
            }
        }
    }

    stage('Run trigger all nightlies') {
        parallel build_for_parallel;
    }

    println("All stages results: ${parallel_stages_states}");
    all_true = parallel_stages_states.every { it == true } == true;
    currentBuild.result = all_true ? "SUCCESS" : "FAILED";
}

return this;
