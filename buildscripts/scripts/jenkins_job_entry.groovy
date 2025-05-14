#!groovy

/// file: jenkins_job_entry.groovy

/// This is the branch specific Checkmk main entry point. It exists to
/// avoid redundant code in the actual job definition files and to be able
/// to provide a standard environment for all Checkmk jobs
import java.text.SimpleDateFormat
import org.jenkinsci.plugins.pipeline.modeldefinition.Utils


def main(job_definition_file) {
    /// brings raise, load_json, cmd_output
    load("${checkout_dir}/buildscripts/scripts/utils/common.groovy");
    load("${checkout_dir}/buildscripts/scripts/utils/docker_util.groovy");

    docker_registry_no_http = DOCKER_REGISTRY.split('://')[1];

    /// in order to spoiler spooky effects encountered just
    /// before midnight we keep a single date for the whole
    /// job
    // TODO: this should be passed through by trigger-jobs
    build_date = (new SimpleDateFormat("yyyy.MM.dd")).format(new Date());

    job_params_from_comments = arguments_from_comments();

    /// map edition short forms to long forms if applicable
    if ("editions" in job_params_from_comments) {
        /// Might also be taken from editions.yml - there we also have 'saas' and 'raw' but
        /// AFAIK there is no way to extract the editions we want to test generically, so we
        /// hard-code these:
        job_params_from_comments["editions"] = job_params_from_comments["editions"].collect {
            [
                "cee": "enterpise",
                "cre": "raw",
                "cme": "managed",
                "cse": "saas",
                "cce": "cloud",
            ].get(it, it)
        };
    }

    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");
    try {
        withCredentialFileAtLocation(credentialsId:"remote.bazelrc", location:"${checkout_dir}/remote.bazelrc") {
            load("${checkout_dir}/${job_definition_file}").main();
        }
    } catch(Exception exc) {
        dir("${checkout_dir}") {
            notify.notify_error(exc);
        }
        throw exc;
    }
}

return this;
