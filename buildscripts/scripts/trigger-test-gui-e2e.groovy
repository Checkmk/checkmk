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

    def package_helper = load("${checkout_dir}/buildscripts/scripts/utils/package_helper.groovy");

    /// This will get us the location to e.g. "checkmk/master" or "Testing/<name>/checkmk/master"
    def branch_base_folder = package_helper.branch_base_folder(with_testing_prefix: true);

    def all_editions = ["enterprise", "cloud", "managed", "raw", "saas"];
    def selected_editions_default = ["enterprise", "cloud", "saas"];
    def params_editions = params.CIPARAM_OVERRIDE_EDITIONS.replaceAll(',', ' ').split(' ').grep();
    def selected_editions = [];
    if (params_editions) {
      selected_editions = params_editions;
    } else if ("editions" in job_params_from_comments) {
      selected_editions = job_params_from_comments.get("editions");
    } else {
      selected_editions = selected_editions_default;
    }

    print(
        """
        |===== CONFIGURATION ===============================
        |all_editions:....... │${all_editions}│
        |selected_edtions:... │${selected_editions}│
        |branch_base_folder:. │${branch_base_folder}│
        |===================================================
        """.stripMargin());
    currentBuild.description += "<br>Selected editions: <b>${selected_editions.join(" ")}</b>";

    def stages = all_editions.collectEntries { edition ->
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
                    // see global-defaults.yml, needs to run in minimal container
                    use_upstream_build: true,
                    relative_job_name: "${branch_base_folder}/builders/test-gui-e2e-f12less",
                    build_params: [
                        CUSTOM_GIT_REF: effective_git_ref,
                        EDITION: edition,
                    ],
                    build_params_no_check: [
                        CIPARAM_OVERRIDE_BUILD_NODE: params.CIPARAM_OVERRIDE_BUILD_NODE,
                        CIPARAM_CLEANUP_WORKSPACE: params.CIPARAM_CLEANUP_WORKSPACE,
                        CIPARAM_BISECT_COMMENT: params.CIPARAM_BISECT_COMMENT,
                    ],
                    no_remove_others: true, // do not delete other files in the dest dir
                    download: false,    // use copyArtifacts to avoid nested directories
                );
            }
        }]
    }

    inside_container_minimal(safe_branch_name: safe_branch_name) {
        currentBuild.result = parallel(stages).values().every { it } ? "SUCCESS" : "FAILURE";
    }
}

return this;
