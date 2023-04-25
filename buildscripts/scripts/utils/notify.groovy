#!groovy

/// file: notify.groovy

import org.codehaus.groovy.runtime.StackTraceUtils;

def get_author_email() {
    // Workaround since CHANGE_AUTHOR_EMAIL is not available
    // Bug: https://issues.jenkins-ci.org/browse/JENKINS-39838
    return (
        onWindows ?
        /// windows will replace %ae with ae..
        cmd_output('git log -1 --pretty=format:%%ae') :
        cmd_output('git log -1 --pretty=format:%ae'))
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


def notify_error(error) {
    // It seems the option "Allowed domains" is not working properly.
    // See: https://ci.lan.tribe29.com/configure
    // So ensure here we only notify internal addresses.
    try {
        def isChangeValidation = currentBuild.fullProjectName.contains("change_validation");
        print("|| error-reporting: isChangeValidation=${isChangeValidation}");

        def isTesting = currentBuild.fullProjectName.contains("Testing");
        print("|| error-reporting: isTesting=${isTesting}");

        def isTriggerJob = currentBuild.fullProjectName.contains("trigger");
        print("|| error-reporting: isTriggerJob=${isTriggerJob}");

        /// for now we assume this build to be in state "FAILURE"
        def isFirstFailure = currentBuild.getPreviousBuild()?.result != "FAILURE";
        print("|| error-reporting: isFirstFailure=${isFirstFailure}");

        if (isFirstFailure && !isChangeValidation && !isTriggerJob && !isTesting) {
            /// include me for now to give me the chance to debug
            def notify_emails = [
                "timotheus.bachinger@tribe29.com",
                "frans.fuerst@tribe29.com",
            ];
            currentBuild.changeSets.each { changeSet ->
                print("|| error-reporting:   changeSet=${changeSet}");
                print("|| error-reporting:   changeSet.items=${changeSet.items}");

                def culprits_emails = changeSet.items.collect {e -> e.authorEmail};
                print("|| error-reporting:   culprits_emails ${culprits_emails}");

                notify_emails += culprits_emails;
                print("|| error-reporting:   notify_emails ${notify_emails}");
            }

            // It seems the option "Allowed domains" is not working properly.
            // See: https://ci.lan.tribe29.com/configure
            // So ensure here we only notify internal addresses.
            notify_emails = notify_emails.unique(false).findAll({
                it != "weblate@checkmk.com" && it.endsWith("@tribe29.com")
            });

            /// Inform cloud devs if cloud burns
            if (currentBuild.fullProjectName.contains("build-cmk-cloud-images")) {
                notify_emails += "max.linke@tribe29.com"
            }

            /// fallback - for investigation
            notify_emails = notify_emails ?: [
                "timotheus.bachinger@tribe29.com", "frans.fuerst@tribe29.com"];

            print("|| error-reporting: notify_emails ${notify_emails}");

            mail(
                to: "${notify_emails.join(',')}",
                cc: "", // the code owner maybe?
                bcc: "",
                from: "\"Greetings from CI\" <${JENKINS_MAIL}>",
                replyTo: "${TEAM_CI_MAIL}",
                subject: "Build failure in ${env.JOB_NAME}",
                body: ("""
    |The following build failed:
    |    ${env.BUILD_URL}
    |
    |The error message was:
    |    ${error}
    |
    |You get this mail because you are on the list of last submitters to a production critical branch, which just turned red.
    |
    |If you feel you got this mail by mistake, please reply and let's fix this together.
    |""".stripMargin()),
           )
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
