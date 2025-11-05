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
