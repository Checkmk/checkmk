// library for simple string modifications
package lib

// This function runs a test inside of a Jenkins stage
// NAME: Display name of the Stage, should describe the test
// CONDITION: true or false, determening whether the stage has to be run
// DIR: Directory in which the test is executed
// ENV_VARS: Array [] of environment variables needed for the test
// COMMAND: command that should be executed. It should be possible to use this exact
//          command to reproduce the test locally in the coresponding DIR
// TEXT_ON_SKIP: Information that is displayed if the test was skipped
def run(Map args) {
    stage(args.NAME) {
        print("Git Status")
        sh("git status")
        print("Git log")
        sh("git log --oneline -n10")
        GERRIT_CHANGE_ID_BASH = sh(script: 'git show --format=%B  -s | grep Change-Id: | cut -d " " -f2', returnStdout: true).toString().trim()
        if (GERRIT_CHANGE_ID_BASH != GERRIT_CHANGE_ID) {
            print("ERROR: Git checkout has changed!!!")
            sh "exit 1"
        }

        print(args.CONDITION)
        if (args.CONDITION) {
            dir(args.DIR) {
                args.ENV_VARS.add("TEST_CONTAINER=${TEST_CONTAINER}")
                withEnv(args.ENV_VARS) {
                    STATUS = sh(script: ". /bauwelt/bin/bw-setup-jenkins-env ; " + args.COMMAND, returnStatus: true)
                    desc_add_status_row(args.NAME, STATUS)
                    sh('exit ' + STATUS)
                }
            }
        } else {
            println(args.TEXT_ON_SKIP)
            desc_add_status_row(args.NAME, 'skipped')
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
