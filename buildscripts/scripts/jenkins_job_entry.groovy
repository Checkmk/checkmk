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

    if (currentBuild.number % 10 == 0) {
        print("Cleanup git clone (git gc)..");
        dir("${checkout_dir}") {
            cmd_output("git gc");
        }
    }

    docker_registry_no_http = DOCKER_REGISTRY.split('://')[1];

    /// in order to spoiler spooky effects encountered just
    /// before midnight we keep a single date for the whole
    /// job
    // TODO: this should be passed through by trigger-jobs
    build_date = (new SimpleDateFormat("yyyy.MM.dd")).format(new Date());

    // FIXME: should be defined elsewhere
    DOCKER_TAG_FOLDER = "master-latest";

    def notify = load("${checkout_dir}/buildscripts/scripts/utils/notify.groovy");
    try {
        load("${checkout_dir}/${job_definition_file}").main();
    } catch(Exception e) {
        dir("${checkout_dir}") {
            notify.notify_error(e);
        }
    }
}
return this;

