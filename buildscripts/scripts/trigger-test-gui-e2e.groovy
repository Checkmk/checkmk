#!groovy

/// file: trigger-test-gui-e2e.groovy

/// Runs `test-gui-e2e-f12less` for specified editions
/// in separate builds paralelly
import org.jenkinsci.plugins.pipeline.modeldefinition.Utils
import java.util.Base64
import groovy.json.JsonSlurperClassic

/// Process Gerrit comments with embedded arguments
/// - future: allow YAML rather than JSON
/// - future: also parse git commit message
/// Format:
/// start: trigger-test-gui-e2e
/// ---
/// {
///   "editions": ["cse", "cee"]
/// }
/// ---
///
def arguments_from_comments() {
    def comment_msg = new String(Base64.getDecoder().decode(env.GERRIT_EVENT_COMMENT_TEXT ?: ""));
    currentBuild.description += "<br>Gerrit comment:<br>---<br><b>${comment_msg}</b><br>---";

    def matcher = comment_msg =~ /(?s)\n---\n(.*)\n---/;
    if (! matcher.find()) {
        return [];
    }
    def arg_text = matcher.group(1);
    currentBuild.description += "<br>Args from comment:<br>---<br><tt><b>${arg_text.replace("\n", "<br>")}</b></tt><br>---";
    return (new groovy.json.JsonSlurperClassic()).parseText(arg_text);
}

def main() {
    /// make sure the listed parameters are set
    check_job_parameters([
        "CIPARAM_OVERRIDE_EDITIONS",
    ]);
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
    def base_folder = "${currentBuild.fullProjectName.split('/')[0..-2].join('/')}";

    print(
        """
        |===== CONFIGURATION ===============================
        |all_editions:..... │${all_editions}│
        |selected_edtions:. │${selected_editions}│
        |base_folder:...... │${base_folder}│
        |===================================================
        """.stripMargin());
    currentBuild.description += "<br>Selected editions: <b>${selected_editions.join(" ")}</b>";

    currentBuild.result = parallel(
        all_editions.collectEntries { edition -> [
            ("${edition}") : {
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
                    build(
                        job: "${base_folder}/builders/test-gui-e2e-f12less",
                        parameters: [
                            string(name: 'EDITION', value: edition),
                            string(name: 'CUSTOM_GIT_REF', value: effective_git_ref),
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
