#!groovy

/// file: send-werks-to-mailing-lists.groovy

def validate_parameters() {
    if (params.SEND_WERK_MAILS && !params.ADD_WERK_GIT_NOTES) {
        error "Sending the werk mails but not adding the git notes is dangerous: " +
            "We may re-send already published werks again."
    }
}

def build_cmd_options_from_params(send_werk_mails, add_werk_git_notes, assume_no_mails_sent_except, werks_mail_address) {
    // We let the python code fetch the git notes (and not via JJB/groovy) as this may also push the notes.
    def cmd_line = "--do-fetch-git-notes"

    if (send_werk_mails) {
        cmd_line += " --do-send-mail";
    }

    if (add_werk_git_notes) {
        cmd_line += " --do-add-notes --do-push-git-notes";
    }

    if (assume_no_mails_sent_except != "") {
        cmd_line += " --assume-no-notes-but ${assume_no_mails_sent_except}"
    }

    if (werks_mail_address != "") {
        cmd_line += " --mail ${werks_mail_address}"
    }

    return cmd_line
}

def main() {
    check_job_parameters([
        "SEND_WERK_MAILS_OF_BRANCHES",
        "SEND_WERK_MAILS",
        "ADD_WERK_GIT_NOTES",
        "ASSUME_NO_MAILS_SENT_EXCEPT",
        "WERKS_MAIL_ADDRESS",
    ]);

    validate_parameters();
    def docker_args = "${mount_reference_repo_dir} " +
        "-h lists.checkmk.com " +
        "-v /etc/nullmailer:/etc/nullmailer:ro " +
        "-v /var/spool/nullmailer:/var/spool/nullmailer";
    def send_werk_mails_of_branches = params.SEND_WERK_MAILS_OF_BRANCHES.split(" ")
    def send_werk_mails = params.SEND_WERK_MAILS;
    def add_werk_git_notes = params.ADD_WERK_GIT_NOTES;
    def assume_no_mails_sent_except = params.ASSUME_NO_MAILS_SENT_EXCEPT;
    def werks_mail_address = params.WERKS_MAIL_ADDRESS;
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

    stage("Send mails") {
        docker.withRegistry(DOCKER_REGISTRY, 'nexus') {
            docker_image_from_alias("IMAGE_TESTING").inside("${docker_args}") {
                withCredentials([sshUserPrivateKey(credentialsId: "ssh-git-gerrit-jenkins", keyFileVariable: 'keyfile')]) {
                    withEnv(["GIT_SSH_COMMAND=ssh -o \"StrictHostKeyChecking no\" -i ${keyfile} -l jenkins"]) {
                        dir("${checkout_dir}") {
                            send_werk_mails_of_branches.each{branch ->
                                sh("""
                                    scripts/run-pipenv run python3 -m cmk.utils.werks mail \
                                    . origin/${branch} werk_mail ${cmd_line};
                                """);
                            }
                        }
                    }
                }
            }
        }
    }
}
return this;
