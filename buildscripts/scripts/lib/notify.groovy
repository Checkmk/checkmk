// library for simple string modifications
package lib


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

def notify_error(error) {
    slack_build_failed(error)
    // after notifying everybody, the error needs to be thrown again
    // This ensures that the build status is set correctly
    throw error
}

return this
