// library for simple string modifications
package lib
// Workaround since CHANGE_AUTHOR_EMAIL is not available
// Bug: https://issues.jenkins-ci.org/browse/JENKINS-39838
AUTHOR_MAIL = sh(script: "git log -1 --pretty=format:%ae", returnStdout: true).toString().trim()


// Send a build failed massage to jenkins
def slack_build_failed(error) {
    def SLACK_ERROR_MESSAGE = """
Build Failed:
    ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)
Error Message:
    ${error}
"""
    slackSend(
        botUser: true,
        color: 'danger',
        message: SLACK_ERROR_MESSAGE
    )
}

// Send a build failed message via mail
def mail_build_failed(error) {
    mail(
        to: AUTHOR_MAIL,
        cc: '',
        bcc: '',
        from: JENKINS_MAIL,
        replyTo: '',
        subject: "Error in ${env.JOB_NAME}",
        body: """
Build Failed:
    ${env.JOB_NAME} ${env.BUILD_NUMBER}
    ${env.BUILD_URL}
Error Message:
    ${error}
                """
   )
}

def notify_error(error) {
    mail_build_failed(error)
    slack_build_failed(error)
    // after notifying everybody, the error needs to be thrown again
    // This ensures that the build status is set correctly
    throw error
}

return this
