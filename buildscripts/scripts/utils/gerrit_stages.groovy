#!groovy

/// file: gerrit_stages.groovy

import org.jenkinsci.plugins.pipeline.modeldefinition.Utils

def log_stage_duration(last_stage_date) {
    def this_stage_date = new Date();   // groovylint-disable NoJavaUtilDate
    def duration = groovy.time.TimeCategory.minus(
        this_stage_date,
        last_stage_date,
    );
    println("+ Stage duration: ${duration}");
    return this_stage_date;
}

// Creates a stage with provided properties. The created stage will be marked as
// successful or failed if its command returns with non-zero and can thus be used
// to implement tests.
// NAME:     Display name of the Stage, should describe the test
// SKIPPED:  Only available when stage shall be skipped. Contains information to be
//           displayed if the test was skipped
// DIR:      Directory in which the test is executed
// ENV_VARS: Array [] of environment variables needed for the test
// COMMAND:  command that should be executed. It should be possible to use this exact
//           command to reproduce the test locally in the coresponding DIR
// JENKINS_API_ACCESS: boolean that configures if env variables for Jenkins API access are present.
def create_stage(Map args, time_stage_started) {
    def duration;
    def issues = [];
    stage(args.NAME) {
        if (args.SKIPPED) {
            Utils.markStageSkippedForConditional(STAGE_NAME);
            println("SKIPPED: ${args.SKIPPED}");
            duration = groovy.time.TimeCategory.minus(new Date(), time_stage_started);
            desc_add_status_row(args.NAME, duration, 'skipped', '--');
            return [true, issues];
        }

        println("CMD: ${args.COMMAND}");
        def cmd_status;

        // We can't use the arguments from SEC_VAR_LIST for accessing the API credentials, because
        // this does not work with the credential type of our API token (username + password).
        // Since we need to bind the values to multiple variables that will be usable later in
        // the job we hardcode these.
        def credentials = args.SEC_VAR_LIST.collect{string(credentialsId: it, variable: it)}
        if (args.JENKINS_API_ACCESS) {
            credentials.add(usernamePassword(
                credentialsId: 'jenkins-api-token',
                usernameVariable: 'JENKINS_USERNAME',
                passwordVariable: 'JENKINS_PASSWORD'
            ))
        }

        withCredentials(credentials) {
            withEnv(args.ENV_VAR_LIST) {
                catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                    dir(args.DIR) {
                        // be very carefull here. Setting quantity to 0 or null, takes all available resources
                        if (args.BAZEL_LOCKS_AMOUNT >= 1) {
                            lock(label: 'bzl_lock_' + env.NODE_NAME.split("\\.")[0].split("-")[-1], quantity: args.BAZEL_LOCKS_AMOUNT, resource : null) {
                                cmd_status = sh(script: args.COMMAND, returnStatus: true);
                            }
                        } else {
                            cmd_status = sh(script: args.COMMAND, returnStatus: true);
                        }
                    }
                    duration = groovy.time.TimeCategory.minus(new Date(), time_stage_started);
                    desc_add_status_row(
                        args.NAME,
                        duration, cmd_status==0 ? "success" : "failure",
                        "${args.RESULT_CHECK_FILE_PATTERN}"
                    );

                    println("Check results: ${args.RESULT_CHECK_TYPE}");
                    if (args.RESULT_CHECK_TYPE) {
                        issues = test_jenkins_helper.analyse_issues(
                            args.RESULT_CHECK_TYPE,
                            args.RESULT_CHECK_FILE_PATTERN,
                            false
                        );
                    }

                    /// make the stage fail if the command returned nonzero
                    sh("exit ${cmd_status}");
                }
            }
        }
        return [cmd_status == 0, issues];
    }
}

def desc_init() {
    // add new content to next line, but do not overwrite existing content
    currentBuild.description += "<br>";
}

def desc_add_line(TEXT) {
    currentBuild.description += "<p>${TEXT}</p>";
}

def desc_add_table_head() {
    currentBuild.description += "<table>";
}

def desc_add_table_bottom() {
    currentBuild.description += "</table>";
}

def desc_add_table() {
    desc_add_table_head();
    desc_add_table_bottom();
}

def desc_rm_table_bottom() {
    currentBuild.description -= "</table>";
}

def desc_add_row(ITEM_1, ITEM_2, ITEM_3, ITEM_4) {
    desc_rm_table_bottom();
    currentBuild.description += """<tr>
    <td>${ITEM_1}</td><td>${ITEM_2}</td><td>${ITEM_3}</td><td>${ITEM_4}</td>
    </tr>""";
    desc_add_table_bottom();
}

def desc_add_status_row(STAGE, DURATION, status, PATTERN) {
    desc_rm_table_bottom();
    if (PATTERN != '' && PATTERN != '--') {
        PATTERN = "<a href=\"artifact/${PATTERN}\">${PATTERN}</a>";
    }
    currentBuild.description += """<tr>
    <td>${STAGE}</td>
    <td>${DURATION}</td>
    <td style=\"color: ${['success': 'green', 'skipped': 'grey', 'failure': 'red'][status]};\">${status}</td>
    <td>${PATTERN}</td>
    </tr>""";
    desc_add_table_bottom();
}

return this;
