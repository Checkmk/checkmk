#!groovy

import org.codehaus.groovy.runtime.StackTraceUtils;

def get_author_email() {
    // Workaround since CHANGE_AUTHOR_EMAIL is not available
    // Bug: https://issues.jenkins-ci.org/browse/JENKINS-39838
    return cmd_output("git log -1 --pretty=format:%ae");
}

// Send a build failed massage to jenkins
def slack_build_failed(error) {
    slackSend(
        botUser: true,
        color: 'danger',
        message: ("""
            |Build Failed:
            |    ${env.JOB_NAME} ${env.BUILD_NUMBER} (<${env.BUILD_URL}|Open>)
            |Error Message:
            |    ${error}
            |""".stripMargin()),
    )
}

// Send a build failed message via mail
def mail_build_failed(address, error) {
    mail(
        to: address,
        cc: '',
        bcc: '',
        from: JENKINS_MAIL,
        replyTo: '',
        subject: "Error in ${env.JOB_NAME}",
        body: ("""
            |Build Failed:
            |    ${env.JOB_NAME} ${env.BUILD_NUMBER}
            |    ${env.BUILD_URL}
            |Error Message:
            |    ${error}
            |""".stripMargin()),
       )
}

def notify_error(error) {
    // It seems the option "Allowed domains" is not working properly.
    // See: https://ci.lan.tribe29.com/configure
    // So ensure here we only notify internal addresses.
    try {
        def author_mail = get_author_email();
        def is_internal_author = (author_mail.endsWith("@tribe29.com") || 
                                  author_mail.endsWith("@mathias-kettner.de"));

        if (author_mail != "weblate@checkmk.com" && is_internal_author) {
            mail_build_failed(author_mail, error);
        }
    } catch(Exception exc) {
        print("Could not report error by mail - got ${exc}");
    }
    
    // Disabled for the moment. It currently does not work because of some
    // wrong configuration.
    //
    // From the build logs:
    //
    // [Pipeline] slackSend
    // Slack Send Pipeline step running, values are - baseUrl: <empty>,
    // teamDomain: <empty>, channel: build-notifications, color: danger,
    // botUser: true, tokenCredentialId: <empty>, iconEmoji <empty>, username
    // <empty>
    //ERROR: Slack notification failed with exception: java.lang.IllegalArgumentException: the token with the provided ID could not be found and no token was specified
    //
    //slack_build_failed(error)
    // after notifying everybody, the error needs to be thrown again
    // This ensures that the build status is set correctly

    StackTraceUtils.sanitize(error);
    print("ERROR: ${error.stackTrace.head()}: ${error}");
    throw error;
}

return this;
