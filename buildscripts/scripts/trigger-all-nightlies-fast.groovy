#!groovy

/// file: trigger-all-nightlies-fast.groovy

/// This job will trigger all other nightly build chains on a fixed node

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

    for ( edition in all_editions ) {
        def run_condition = edition in editions_to_test;
        println("Should ${edition} be triggered? ${run_condition}");

        smart_stage(
            name: "Trigger ${edition}",
            condition: run_condition,
            raiseOnError: false,
        ) {
            catchError(buildResult: "FAILURE", stageResult: "FAILURE") {
                def this_job_parameters = job_parameters + [$class: 'StringParameterValue', name: 'EDITION', value: edition];

                print(
                    """
                    |===== CONFIGURATION ===============================
                    |this_job_parameters:... │${this_job_parameters}│
                    |===================================================
                    """.stripMargin());

                build(job: "${base_folder}/trigger-cmk-build-chain-${edition}", parameters: this_job_parameters);
            }
        }
    }
}

return this;
