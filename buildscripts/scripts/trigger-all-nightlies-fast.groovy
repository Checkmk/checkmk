#!groovy

/// file: trigger-all-nightlies-fast.groovy

/// This job will trigger all other nightly build chains on a fixed node

def main() {
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}/";
    def versioning = load("${checkout_dir}/buildscripts/scripts/utils/versioning.groovy");
    def editions = versioning.get_editions();

    def job_parameters = [
        [$class: 'StringParameterValue',  name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE],
    ];

    def override_distros = params.EDITIONS.trim() ?: "";
    if (override_distros) {
        editions = override_distros.replaceAll(',', ' ').split(' ').grep();
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |editions:.............. │${editions}│
        |base_folder:........... │${base_folder}│
        |job_parameters:........ │${job_parameters}│
        |fixed_node:............ |${params.TRIGGER_CIPARAM_OVERRIDE_BUILD_NODE}|
        |===================================================
        """.stripMargin());

    for ( edition in editions ) {
        catchError(buildResult: "FAILURE", stageResult: "FAILURE") {
            stage("Trigger ${edition}") {
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
