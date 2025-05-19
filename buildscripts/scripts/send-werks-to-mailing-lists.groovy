#!groovy

/// file: send-werks-to-mailing-lists.groovy

def validate_parameters(send_werk_mails, add_werk_git_notes) {
    if (send_werk_mails && !add_werk_git_notes) {
        error("Sending the werk mails but not adding the git notes is dangerous: " +
            "We may re-send already published werks again.");
    }
}

def build_cmd_options_from_params(send_werk_mails, add_werk_git_notes, assume_no_mails_sent_except, werks_mail_address) {
    // We let the python code fetch the git notes (and not via JJB/groovy) as this may also push the notes.
    def cmd_line = "--do-fetch-git-notes";

    if (send_werk_mails) {
        cmd_line += " --do-send-mail";
    }

    if (add_werk_git_notes) {
        cmd_line += " --do-add-notes --do-push-git-notes";
    }

    if (assume_no_mails_sent_except != "") {
        cmd_line += " --assume-no-notes-but ${assume_no_mails_sent_except}";
    }

    if (werks_mail_address != "") {
        cmd_line += " --mail ${werks_mail_address}";
    }

    return cmd_line;
}

def was_timer_triggered() {
    return currentBuild.rawBuild.getCauses()[0].toString().contains('TimerTriggerCause');
}

def main() {
    if (params.CUSTOM_GIT_REF != "") {
       raise("The werk jobs are not meant to be triggered with a custom git ref to no miss any werks.");
    }

    check_job_parameters([
        "SEND_WERK_MAILS_OF_BRANCHES",
        "SEND_WERK_MAILS",
        "ADD_WERK_GIT_NOTES",
        "ASSUME_NO_MAILS_SENT_EXCEPT",
        "WERKS_MAIL_ADDRESS",
    ]);

    def docker_args = [
        "-h lists.checkmk.com ",
        "-v /etc/nullmailer:/etc/nullmailer:ro ",
        "-v /var/spool/nullmailer:/var/spool/nullmailer",
    ];
    def send_werk_mails_of_branches = params.SEND_WERK_MAILS_OF_BRANCHES.split(" ");
    def send_werk_mails = params.SEND_WERK_MAILS;
    def add_werk_git_notes = params.ADD_WERK_GIT_NOTES;
    def assume_no_mails_sent_except = params.ASSUME_NO_MAILS_SENT_EXCEPT;
    def werks_mail_address = params.WERKS_MAIL_ADDRESS;

    if (was_timer_triggered()) {
        println("Current job was triggered by Timer, so we need to use the production parameters.");
        send_werk_mails_of_branches = ["master", "2.4.0", "2.3.0", "2.2.0", "2.1.0", "2.0.0"];
        send_werk_mails = true;
        add_werk_git_notes = true;
        assume_no_mails_sent_except = "";
        werks_mail_address = "";
    }
    validate_parameters(send_werk_mails, add_werk_git_notes);
    def cmd_line = build_cmd_options_from_params(send_werk_mails, add_werk_git_notes, assume_no_mails_sent_except, werks_mail_address);

    print(
        """
        |===== CONFIGURATION ===============================
        |docker_args:................ │${docker_args}│
        |checkout_dir:............... │${checkout_dir}│
        |send_werk_mails_of_branches: │${send_werk_mails_of_branches}│
        |send_werk_mails:............ │${send_werk_mails}│
        |add_werk_git_notes:......... │${add_werk_git_notes}│
        |assume_no_mails_sent_except: │${assume_no_mails_sent_except}│
        |werks_mail_address:......... │${werks_mail_address}│
        |cmd_line:................... │${cmd_line}│
        |===================================================
        """.stripMargin());

    stage("Checkout repositories") {
        // this will checkout the repo at "${WORKSPACE}/${repo_name}"
        // but check again if you modify it here
        provide_clone("check_mk", "jenkins-gerrit-fips-compliant-ssh-key");

        // check_mk has to be on master
        dir("${WORKSPACE}/check_mk") {
            sh("git checkout master");
        }
    }

    stage("Send mails") {
        inside_container(args: docker_args) {
            withCredentials([
                sshUserPrivateKey(credentialsId: "jenkins-gerrit-fips-compliant-ssh-key", keyFileVariable: 'keyfile', usernameVariable: 'user')
            ]) {
                withEnv(["GIT_SSH_COMMAND=ssh -o \"StrictHostKeyChecking no\" -i ${keyfile} -l ${user}"]) {
                    dir("${checkout_dir}") {
                        send_werk_mails_of_branches.each{branch ->
                            sh("""
                                git config --add user.name ${user};
                                git config --add user.email ${JENKINS_MAIL};
                                scripts/run-uvenv python3 -m cmk.utils.werks mail \
                                ${WORKSPACE}/check_mk origin/${branch} werk_mail ${cmd_line};
                            """);
                        }
                    }
                }
            }
        }
    }
}

return this;
