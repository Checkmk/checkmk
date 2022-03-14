// library for simple string modifications
package lib
import groovy.json.JsonSlurperClassic


// Runs provided command in a shell and returns the JSON parsed stdout output
def load_json(json_file) {
    def cmd_stdout_result = sh(script: "cat ${json_file}", returnStdout: true);
    (new groovy.json.JsonSlurperClassic()).parseText(cmd_stdout_result);
}

def log_stage_duration(last_stage_date) {
    def this_stage_date = new Date();
    def duration = groovy.time.TimeCategory.minus(
        this_stage_date,
        last_stage_date,
    );
    println("+ Stage duration: " + duration);
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
def create_stage(Map args, issues, time_stage_started) {
    def duration;
    stage(args.NAME) {
        if (args.SKIPPED) {
            println("SKIPPED: ${args.SKIPPED}");
            duration = groovy.time.TimeCategory.minus(new Date(), time_stage_started);
            desc_add_status_row(args.NAME, duration, 'skipped', '--');
            return true;
        }

        sh(script: "figlet -w 150 '${args.NAME}'", returnStatus: true);
        println("CMD: ${args.COMMAND}")
        def cmd_status;
        withEnv(args.ENV_VAR_LIST) {
            catchError(buildResult: 'SUCCESS', stageResult: 'FAILURE') {
                dir(args.DIR) {
                    cmd_status = sh(script: args.COMMAND, returnStatus: true);
                }
                duration = groovy.time.TimeCategory.minus(new Date(), time_stage_started);
                desc_add_status_row(args.NAME, duration, cmd_status, "${args.RESULT_CHECK_FILE_PATTERN}");

                println("Check results: ${args.RESULT_CHECK_TYPE}");
                if (args.RESULT_CHECK_TYPE) {
                    if (args.RESULT_CHECK_TYPE == "MYPY") {
                        issues.add(scanForIssues(
                            tool: myPy(pattern: "${args.RESULT_CHECK_FILE_PATTERN}")));
                    } else if (args.RESULT_CHECK_TYPE == "PYLINT") {
                        issues.add(scanForIssues(
                            tool: pyLint(pattern: "${args.RESULT_CHECK_FILE_PATTERN}")));
                    } else if (args.RESULT_CHECK_TYPE == "GCC") {
                        issues.add(scanForIssues(
                            tool: gcc(pattern: "${args.RESULT_CHECK_FILE_PATTERN}")));
                    } else if (args.RESULT_CHECK_TYPE == "CLANG") {
                        issues.add(scanForIssues(
                            tool: clang(pattern: "${args.RESULT_CHECK_FILE_PATTERN}")));
                    }
                }
                /// make the stage fail if the command returned nonzero
                sh('exit ' + cmd_status);
            }
        }
        return cmd_status == 0;
    }
}


// Functions to add status of stages in from of tables
def desc_init() {
    currentBuild.description = ""
}
def desc_add_line(TEXT) {
    currentBuild.description += '<p>' + TEXT + '</p>'
}
def desc_add_table_head() {
    currentBuild.description += '<table>'
}
def desc_add_table_bottom() {
    currentBuild.description += '</table>'
}
def desc_add_table() {
    desc_add_table_head()
    desc_add_table_bottom()
}
def desc_rm_table_bottom() {
    currentBuild.description -= '</table>'
}
def desc_add_row(ITEM_1, ITEM_2, ITEM_3, ITEM_4) {
    desc_rm_table_bottom()
    currentBuild.description += '<tr><td>' + ITEM_1 + '</td><td>' + ITEM_2 + '</td><td>' + ITEM_3 + '</td><td>' + ITEM_4 + '</td></tr>'
    desc_add_table_bottom()
}
def desc_add_status_row(STAGE, DURATION, STATUS, PATTERN) {
    desc_rm_table_bottom()
    if (STATUS == 0) {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td>' + DURATION + '</td><td style="color: green;">success</td><td>' + PATTERN + '</td></tr>'
    } else if (STATUS == 'skipped') {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td>' + DURATION + '</td><td style="color: grey;">skipped</td><td>' + PATTERN + '</td></tr>'
    } else {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td>' + DURATION + '</td><td style="color: red;">failed</td><td>' + PATTERN + '</td></tr>'
    }
    desc_add_table_bottom()
}

return this
