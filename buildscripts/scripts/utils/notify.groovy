#!groovy

/// file: notify.groovy

def notify_error(error) {
    // It seems the option "Allowed domains" is not working properly.
    // See: https://ci.lan.tribe29.com/configure
    // So ensure here we only notify internal addresses.
    def projectname = currentBuild.fullProjectName;
    def email_address_team_werks = ["benedikt.seidl@checkmk.com"];

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

            /// Inform nile devs if our extensions fail
            if (projectname.contains("test-extension-compatibility")) {
                notify_emails.addAll(TEAM_NILE_MAIL.split(","));
            }

            /// Inform werk workers if something's wrong with the werk jobs
            if (projectname.startsWith("werks/")) {
                notify_emails.addAll(email_address_team_werks);
            }

            /// Inform QA if something's wrong with those jobs
            if (projectname.contains("test-plugins") || projectname.contains("test-update")) {
                notify_emails.addAll(TEAM_QA_MAIL.replaceAll(',', ' ').split(' ').grep());
            }

            /// fallback - for investigation
            notify_emails = notify_emails ?: TEAM_CI_MAIL.split(",");

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
}

return this;
