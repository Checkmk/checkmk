#!groovy

/// file: notify.groovy

def get_author_email() {
    // Workaround since CHANGE_AUTHOR_EMAIL is not available
    // Bug: https://issues.jenkins-ci.org/browse/JENKINS-39838
    return (
        onWindows ?
            /// windows will replace %ae with ae..
            cmd_output('git log -1 --pretty=format:%%ae') :
            cmd_output('git log -1 --pretty=format:%ae'));
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
    );
}

def notify_maintainer_of_package(maintainers, package_name, build_url) {
    try {
        mail(
            to: maintainers.join(","),  // TODO: Add the commmiter
            cc: maintainers.join(","),
            bcc: "",
            from: "\"CI\" <${JENKINS_MAIL}>",
            replyTo: "${TEAM_CI_MAIL}",
            subject: "[${package_name} failed]",
            body: ("""
    |The following package has failed - check the console log here:
    |    ${build_url}
    |""".stripMargin()),
        );
    } catch (Exception exc) {    // groovylint-disable CatchException
        println("Could not sent mail to package owner - got ${exc}");
    }
}

def notify_error(error) {
    // It seems the option "Allowed domains" is not working properly.
    // See: https://ci.lan.tribe29.com/configure
    // So ensure here we only notify internal addresses.
    def projectname = currentBuild.fullProjectName;
    try {
        def isChangeValidation = projectname.contains("cv");
        def isTesting = projectname.contains("Testing");
        def isTriggerJob = projectname.contains("trigger");
        /// for now we assume this build to be in state "FAILURE"
        def isFirstFailure = currentBuild.getPreviousBuild()?.result != "FAILURE";
        print(
            """
            ||==========================================================================================
            || error-reporting: isChangeValidation=${isChangeValidation}
            || error-reporting: isTesting=${isTesting}
            || error-reporting: isTriggerJob=${isTriggerJob}
            || error-reporting: isFirstFailure=${isFirstFailure}
            ||==========================================================================================
            """.stripMargin());

        if (isFirstFailure && !isChangeValidation && !isTriggerJob && !isTesting) {
            /// include me for now to give me the chance to debug
            def notify_emails = [];
            // ugly workaround, split() only + unique() does not work
            notify_emails.addAll(TEAM_CI_MAIL.replaceAll(',', ' ').split(' ').grep());
            currentBuild.changeSets.each { changeSet ->
                def culprits_emails = changeSet.items.collect { e -> e.authorEmail };
                print(
                    """
                    ||==========================================================================================
                    || error-reporting:   changeSet=${changeSet}
                    || error-reporting:   changeSet.items=${changeSet.items}
                    || error-reporting:   culprits_emails=${culprits_emails}
                    ||==========================================================================================
                    """.stripMargin());
            }

            // It seems the option "Allowed domains" is not working properly.
            // See: https://ci.lan.tribe29.com/configure
            // So ensure here we only notify internal addresses.
            notify_emails = notify_emails.unique(false).findAll({
                it != "weblate@checkmk.com" && it.endsWith("@checkmk.com")
            });

            /// Inform cloud devs if cloud burns
            if (projectname.contains("build-cmk-cloud-images") || projectname.contains("saas")) {
                notify_emails += "aws-saas-checkmk-dev@checkmk.com";
            }

            /// Inform nile devs if our extensions fail
            if (projectname.contains("test-extension-compatibility")) {
                notify_emails.addAll(TEAM_NILE_MAIL.split(","));
            }

            /// Inform werk workers if something's wrong with the werk jobs
            if (projectname.startsWith("werks/")) {
                notify_emails += "benedikt.seidl@checkmk.com";
            }

            /// Inform QA if something's wrong with those jobs
            if (projectname.contains("test-plugins") || projectname.contains("test-update")) {
                notify_emails += "matteo.stifano@checkmk.com";
                notify_emails += "rene.slowenski@checkmk.com";
            }

            /// fallback - for investigation
            /* groovylint-disable DuplicateListLiteral */
            notify_emails = notify_emails ?: [
                "timotheus.bachinger@checkmk.com",
                "frans.fuerst@checkmk.com",
                "jonas.scharpf@checkmk.com",
            ];
            /* groovylint-enable DuplicateListLiteral */

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
            );
        }
    } catch (Exception exc) {    // groovylint-disable CatchException
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
    //ERROR: Slack notification failed with exception:
    //java.lang.IllegalArgumentException: the token with the provided ID could not be found and no token was specified
    //
    //slack_build_failed(error)
    // after notifying everybody, the error needs to be thrown again
    // This ensures that the build status is set correctly
}

return this;
