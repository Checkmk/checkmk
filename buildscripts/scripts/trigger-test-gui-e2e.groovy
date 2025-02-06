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

    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    /// Might also be taken from editions.yml - there we also have 'saas' and 'raw' but
    /// AFAIK there is no way to extract the editions we want to test generically, so we
    /// hard-code these:
    def editions_from_comment = arguments_from_comments()["editions"].collect {
        [
            "cee": "enterpise",
            "cre": "raw",
            "cme": "managed",
            "cse": "saas",
            "cce": "cloud",
        ].get(it, it)
    };
    def all_editions = ["enterprise", "cloud", "managed", "raw", "saas"];
    def selected_editions_default = ["enterprise", "cloud", "saas"];
    def selected_editions = (
        params.CIPARAM_OVERRIDE_EDITIONS.replaceAll(',', ' ').split(' ').grep()
        ?: editions_from_comment
        ?: selected_editions_default
    );

    print(
        """
        |===== CONFIGURATION ===============================
        |all_editions:....... │${all_editions}│
        |selected_edtions:... │${selected_editions}│
        |branch_base_folder:. │${branch_base_folder}│
        |===================================================
        """.stripMargin());
    currentBuild.description += "<br>Selected editions: <b>${selected_editions.join(" ")}</b>";

    currentBuild.result = parallel(
        all_editions.collectEntries { edition ->
            [("${edition}") : {
                def run_condition = edition in selected_editions;
                /// this makes sure the whole parallel thread is marked as skipped
                if (! run_condition){
                    Utils.markStageSkippedForConditional("${edition}");
                }
                smart_stage(
                    name: "Test ${edition}",
                    condition: run_condition,
                    raiseOnError: false,
                ) {
                    smart_build(
                        job: "${branch_base_folder}/builders/test-gui-e2e-f12less",
                        parameters: [
                            stringParam(name: 'EDITION', value: edition),
                            stringParam(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
                            stringParam(name: 'CIPARAM_OVERRIDE_BUILD_NODE', value: params.CIPARAM_OVERRIDE_BUILD_NODE),
                            stringParam(name: 'CIPARAM_CLEANUP_WORKSPACE', value: params.CIPARAM_CLEANUP_WORKSPACE),
                        ]
                    );
                }
            }]
        }
    ).values().every { it } ? "SUCCESS" : "FAILURE";
}

return this;
