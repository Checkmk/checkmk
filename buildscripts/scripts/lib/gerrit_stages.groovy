// library for simple string modifications
package lib
import groovy.json.JsonSlurperClassic


// Runs provided command in a shell and returns the JSON parsed stdout output
def load_json(json_file) {
    def cmd_stdout_result = sh(script: "cat ${json_file}", returnStdout: true);
    (new groovy.json.JsonSlurperClassic()).parseText(cmd_stdout_result);
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
def create_stage(Map args) {
    stage(args.NAME) {
        if (args.SKIPPED) {
            println("SKIPPED: ${args.SKIPPED}")
            desc_add_status_row(args.NAME, 'skipped')
        } else {
            println("CMD: ${args.COMMAND}")
            dir(args.DIR) {
                withEnv(args.ENV_VAR_LIST) {
                    def cmd_status = sh(script: args.COMMAND, returnStatus: true)
                    desc_add_status_row(args.NAME, cmd_status)
                    sh('exit ' + cmd_status)
                }
            }
        }
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
def desc_add_row(ITEM_1, ITEM_2) {
    desc_rm_table_bottom()
    currentBuild.description += '<tr><td>' + ITEM_1 + '</td><td>' + ITEM_2 + '</td></tr>'
    desc_add_table_bottom()
}
def desc_add_status_row(STAGE, STATUS) {
    desc_rm_table_bottom()
    if (STATUS == 0) {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td style="color: green;">success</td></tr>'
    } else if (STATUS == 'skipped') {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td style="color: grey;">skipped</td></tr>'
    } else {
        currentBuild.description += '<tr><td>' + STAGE + '</td><td style="color: red;">failed</td></tr>'
    }
    desc_add_table_bottom()
}

return this
