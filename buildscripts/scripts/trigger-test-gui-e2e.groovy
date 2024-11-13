#!groovy

/// file: trigger-test-gui-e2e.groovy

/// Runs `test-gui-e2e-f12less` for specified editions
/// in separate builds paralelly
import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "CIPARAM_OVERRIDE_EDITIONS",
    ]);
    /// Might also be taken from editions.yml - there we also have 'saas' and 'raw' but
    /// AFAIK there is no way to extract the editions we want to test generically, so we
    /// hard-code these:
    def all_editions = ["enterprise", "cloud", "managed"];
    def editions = params.CIPARAM_OVERRIDE_EDITIONS.replaceAll(',', ' ').split(' ').grep() ?: all_editions;
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}";

    print(
        """
        |===== CONFIGURATION ===============================
        |all_editions:.. │${all_editions}│
        |editions:...... │${editions}│
        |base_folder:... │${base_folder}│
        |===================================================
        """.stripMargin());

    currentBuild.result = parallel(
        all_editions.collectEntries { edition -> [
            ("${edition}") : {
                def run_condition = edition in editions;
                /// this makes sure the whole parallel thread is marked as skipped
                if (! run_condition){
                    Utils.markStageSkippedForConditional("${edition}");
                }
                smart_stage(
                    name: "Test ${edition}",
                    condition: run_condition,
                    raiseOnError: false,
                ) {
                    build(
                        job: "${base_folder}/builders/test-gui-e2e-f12less",
                        parameters: [
                            string(name: 'EDITION', value: edition),
                            string(name: 'CUSTOM_GIT_REF', value: params.CUSTOM_GIT_REF),
                            string(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                            string(name: 'CIPARAM_CLEANUP_WORKSPACE', value: params.CIPARAM_CLEANUP_WORKSPACE),
                        ]
                    );
                }
            }]
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;

